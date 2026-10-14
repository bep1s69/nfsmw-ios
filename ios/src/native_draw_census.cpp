// Native renderer, step 1: a census of the game's Direct3D draw path, and a
// capture of the complete state of one frame's draws.
//
// NFSMW links the Xbox 360 D3D library with link-time code generation, so
// most of D3D is inlined into the game; the draws are not. These functions
// write the GPU's draw commands (PM4 type-3 DRAW_INDX 0x22 / DRAW_INDX_2 0x36,
// predicated for tiled rendering), found by those command constants in the
// recompiled code:
//
//   sub_82593818  DrawVertices(device, primitive, start vertex, vertex count)
//   sub_82593A58  DrawIndexedVertices(device, primitive, base vertex,
//                 start index, index count); index buffer at device+12532
//   sub_825930E0  another DRAW_INDX writer (via sub_82593390)
//   sub_82593408  another DRAW_INDX writer (via sub_82593748)
//   sub_8259A308  inline vertices (DRAW_INDX_2)
//   sub_82592340  Resolve (EVENT_WRITE, SET_CONSTANT, WAIT_REG_MEM, a quad);
//                 ~14 a frame in the menu, ~21 in a race, as the SDK counted
//   sub_825987E0  Swap (calls VdSwap)
//
// All the draws start by flushing the device's changed state (sub_825A3EC8)
// into the ring. The device keeps the address of the last dword written to
// the ring at +0 and the end of the current segment at +8, a 64-bit dirty
// mask at +32 and the texture fetch constants at +1152 (24 bytes each).
//
// The census (nfsmw_draw_census) counts the calls, every 5 s.
//
// The capture (nfsmw_draw_capture) decodes what each draw wrote into the ring,
// so it does not depend on the device's layout: a register file kept from the
// SET_CONSTANT / type-0 packets, the shaders from IM_LOAD(_IMMEDIATE), the
// draw from DRAW_INDX(_2). Every 30 s it logs one whole frame, Swap to Swap:
// a line per draw (shaders, render targets, render state, the textures and
// vertex buffers bound by that draw), the passes, and the frame's distinct
// shaders and textures. That is what the native renderer has to reproduce.

#include <atomic>
#include <chrono>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include "nfsmw_pch.h"
#include "native_renderer.h"
#include <rex/graphics/xenos.h>

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

REXCVAR_DEFINE_BOOL(nfsmw_draw_census, false, "GPU",
                    "Native renderer bring-up: log the game's D3D draw calls every 5 s");
REXCVAR_DEFINE_BOOL(nfsmw_draw_capture, true, "GPU",
                    "Native renderer bring-up: every 30 s, log the state of every draw of one "
                    "frame");

extern "C" void __imp__sub_82593818(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82593A58(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_825930E0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82593408(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_8259A308(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82592340(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_825987E0(PPCContext& __restrict ctx, uint8_t* base);

namespace {

enum Kind { kDraw, kIndexed, kOther1, kOther2, kInline, kResolve, kKinds };
constexpr const char* kNames[kKinds] = {"DrawVertices",   "DrawIndexedVertices", "sub_825930E0",
                                        "sub_82593408",   "inline (sub_8259A308)",
                                        "resolve (sub_82592340)"};

int64_t NowMs() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

// --- Census ------------------------------------------------------------------

std::atomic<uint64_t> calls[kKinds];
std::atomic<uint64_t> elements[kKinds];  // vertices or indices drawn
std::atomic<uint64_t> primitives[32];    // indexed and plain draws by primitive type
std::atomic<uint32_t> last_device{0};
std::atomic<int64_t> since{0};

void Count(Kind kind, uint32_t device, uint32_t primitive, uint32_t count) {
  calls[kind].fetch_add(1, std::memory_order_relaxed);
  if (kind == kDraw || kind == kIndexed) {
    elements[kind].fetch_add(count, std::memory_order_relaxed);
    primitives[primitive & 31].fetch_add(1, std::memory_order_relaxed);
  }
  last_device.store(device, std::memory_order_relaxed);

  const int64_t now = NowMs();
  int64_t start = since.load(std::memory_order_relaxed);
  if (!start) {
    since.compare_exchange_strong(start, now);
    return;
  }
  if (now - start < 5000 || !since.compare_exchange_strong(start, now)) {
    return;
  }
  REXLOG_INFO("[draw-census] 5 s, device {:#010x}:", last_device.load());
  for (int k = 0; k < kKinds; ++k) {
    const uint64_t n = calls[k].exchange(0);
    const uint64_t e = elements[k].exchange(0);
    if (n) {
      REXLOG_INFO("[draw-census]   {:>24}: {:7d} calls, {:9d} vertices/indices", kNames[k], n, e);
    }
  }
  std::string prims;
  for (int p = 0; p < 32; ++p) {
    if (const uint64_t n = primitives[p].exchange(0)) {
      prims += fmt::format(" {}:{}", p, n);
    }
  }
  REXLOG_INFO("[draw-census]   primitive types (type:draws):{}", prims);
}

// --- Capture -----------------------------------------------------------------

// Xenos registers (Xenia's register_table.inc).
constexpr uint32_t kRbSurfaceInfo = 0x2000;
constexpr uint32_t kRbColorInfo = 0x2001;
constexpr uint32_t kRbDepthInfo = 0x2002;
constexpr uint32_t kRbColor1Info = 0x2003;
constexpr uint32_t kRbColorMask = 0x2104;
constexpr uint32_t kSqProgramCntl = 0x2180;
constexpr uint32_t kRbDepthControl = 0x2200;
constexpr uint32_t kRbBlendControl0 = 0x2201;
constexpr uint32_t kRbColorControl = 0x2202;
constexpr uint32_t kPaSuScModeCntl = 0x2205;
constexpr uint32_t kFetchBase = 0x4800;  // 32 slots x 6 dwords
constexpr uint32_t kAluBase = 0x4000;    // 512 float4 (256 VS + 256 PS)
constexpr uint32_t kRegisterCount = 0x6000;

struct Shader {
  uint32_t address = 0;  // guest physical, 0 if loaded inline
  uint32_t dwords = 0;
  uint64_t hash = 0;
  uint32_t head[4] = {};  // first microcode dwords, to find it in the game files
  uint64_t key = 0;       // the name of its Metal library: hash, vertex fetches zeroed for VS
};

extern "C" void nfsmw_native_probe_pipelines(const uint64_t* pairs, uint32_t count);

class Capture {
 public:
  // Before and after a draw: decodes what it (and anything since the last
  // draw) wrote into the ring.
  void Before(uint32_t device) {
    FlushPending();
    before_ = RingPointer(device);
    in_call_ = true;
    // The draw packet is this draw's own: a stale one (a resolve's) must
    // not be taken for it.
    initiator_ = 0;
    inline_draw_ = false;
  }
  // D3D's "make space" (sub_82597070): when the command buffer segment is
  // full it moves to a new one in the middle of a draw (often right after
  // the big scene pass): the old segment is decoded up to where it ended,
  // the draw continues from the new one.
  void SegmentSwitchBefore(uint32_t device) {
    if (in_call_) {
      const uint32_t end = RingPointer(device);
      if (end >= before_ && end - before_ < (4u << 20)) {
        Parse(before_ + 4, end + 4);
      } else {
        ++gaps_;
      }
    }
  }
  void SegmentSwitchAfter(uint32_t new_pointer) {
    if (in_call_) {
      before_ = new_pointer;
      ++segment_switches_;
    }
  }
  void After(Kind kind, uint32_t device, uint32_t primitive, uint32_t count,
             uint32_t start = 0, uint32_t returned = 0) {
    in_call_ = false;
    const uint32_t after = RingPointer(device);
    // The ring pointer is the last dword written; new packets start 4 past it.
    // Only this draw's own packets: the draw functions flush the device's
    // changed state themselves. (Decoding from the previous draw's end read
    // the gap between two command buffers as packets, e.g. around tiling,
    // and lost sync: 0x3FC00000, a float, taken for a type-0 header zeroed
    // the render target registers.)
    const uint32_t from = before_;
    touched_.clear();
    if (after >= from && after - from < (4u << 20)) {
      Parse(from + 4, after + 4);
    } else {
      ++gaps_;
    }
    last_after_ = after;
    if (recording_) {
      Record(kind, primitive, count);
    }
    // DrawVertices whose draw packet went to D3D's other buffer (the
    // predicated tiling path, device+13536): its arguments say it all
    // (primitive, start vertex, count; auto-generated indices). The state
    // was flushed into the ring before the path split.
    bool from_arguments = false;
    // sub_825930E0 (DrawPrimitiveUP, the menu's 8 post-processing draws a
    // frame: bloom, composite) too: vertex count in its arguments, the
    // vertices from offset 0 of their fetch constant.
    if (initiator_ == 0 && (kind == kDraw || kind == kOther1) && count && count < (1u << 16)) {
      initiator_ = (count << 16) | (2u << 6) | (primitive & 0x3F);
      from_arguments = true;
      if (kind == kOther1) {
        start = 0;
      }
    }
    if (native_frame_ && initiator_ != 0 &&
        (kind == kDraw || kind == kIndexed || kind == kOther1 || kind == kOther2 ||
         kind == kInline)) {
      NfsmwNativeDraw draw = {regs_.data(), vs_code_.data(), uint32_t(vs_code_.size()),
                              vs_.key, ps_.key, initiator_, index_base_, index_size_,
                              inline_draw_ ? 1u : 0u, from_arguments ? 1u : 0u, start,
                              kind == kOther1 ? returned : 0u};
      if (kind == kOther1) {
        // Its vertices are copied in after it returns: handed over at the
        // next GPU call (the registers stay as they are until then).
        pending_ = draw;
        has_pending_ = true;
      } else {
        nfsmw_native_draw(&draw);
      }
    }
  }
  // A DrawPrimitiveUP waiting for its vertices: at the next draw, resolve or
  // swap they are in place.
  void FlushPending() {
    if (has_pending_) {
      has_pending_ = false;
      pending_.regs = regs_.data();
      pending_.vs_microcode = vs_code_.data();
      nfsmw_native_draw(&pending_);
    }
  }
  // Around a resolve: its own packets (the RB_COPY_* registers, the vertex
  // fetch with its rectangle, the event) are decoded like a draw's.
  void ResolveBefore(uint32_t device) {
    FlushPending();
    before_ = RingPointer(device);
    in_call_ = true;
    // D3D restores its own state after a resolve (the scissor, window,
    // surface registers the copy sets are not rewritten by the next draw's
    // flush): the resolve's registers are read, then the file is put back.
    saved_regs_ = regs_;
  }
  void Resolve(uint32_t device) {
    in_call_ = false;
    const uint32_t after = RingPointer(device);
    if (device && after >= before_ && after - before_ < (4u << 20)) {
      Parse(before_ + 4, after + 4);
    } else {
      ++gaps_;
    }
    if (recording_) {
      lines_.push_back(fmt::format("  -- resolve (after draw {})", draw_index_));
      ++resolves_;
    }
    if (native_frame_) {
      nfsmw_native_resolve(regs_.data());
    }
    if (saved_regs_.size() == regs_.size()) {
      regs_.swap(saved_regs_);
    }
  }
  void Swap() {
    FlushPending();
    native_frame_ = nfsmw_native_swap();
    if (recording_) {
      Flush();
      recording_ = false;
      next_ms_ = NowMs() + 15000;
    } else if (NowMs() >= next_ms_) {
      Begin();
    }
  }

 private:
  static rex::memory::Memory* Mem() {
    auto* kernel = rex::system::kernel_state();
    return kernel ? kernel->memory() : nullptr;
  }
  static uint32_t LoadVirtual(uint32_t address) {
    return __builtin_bswap32(*Mem()->TranslateVirtual<const uint32_t*>(address));
  }
  static uint32_t RingPointer(uint32_t device) { return LoadVirtual(device); }

  void Parse(uint32_t from, uint32_t to) {
    uint32_t p = from;
    while (p < to) {
      const uint32_t h = LoadVirtual(p);
      const uint32_t type = h >> 30;
      if (recording_) {
        source_ = fmt::format("type {} header {:08x} at {:08x}", type, h, p);
      }
      if (type == 0) {
        const uint32_t count = ((h >> 16) & 0x3FFF) + 1;
        const uint32_t reg = h & 0x7FFF;
        // Sanity: a header this long, or past the register file, means the
        // decoding lost sync; stop instead of writing garbage.
        if (count > 0x800 || reg + (((h >> 15) & 1) ? 1 : count) > kRegisterCount) {
          ++gaps_;
          return;
        }
        const bool one = (h >> 15) & 1;
        for (uint32_t i = 0; i < count && p + 4 + 4 * i < to; ++i) {
          Write(one ? reg : reg + i, LoadVirtual(p + 4 + 4 * i));
        }
        p += 4 * (count + 1);
      } else if (type == 1) {
        Write(h & 0x7FF, LoadVirtual(p + 4));
        Write((h >> 11) & 0x7FF, LoadVirtual(p + 8));
        p += 12;
      } else if (type == 2) {
        p += 4;
      } else {
        const uint32_t count = ((h >> 16) & 0x3FFF) + 1;
        if (count > 0x2000) {
          ++gaps_;
          return;
        }
        Packet3((h >> 8) & 0x7F, p + 4, count);
        p += 4 * (count + 1);
      }
    }
  }

  void Packet3(uint32_t opcode, uint32_t data, uint32_t count) {
    switch (opcode) {
      case 0x2D: {  // SET_CONSTANT
        const uint32_t d0 = LoadVirtual(data);
        const uint32_t index = d0 & 0x7FF;
        uint32_t base;
        switch ((d0 >> 16) & 0xFF) {
          case 0: base = kAluBase; break;
          case 1: base = kFetchBase; break;
          case 2: base = 0x4900; break;
          case 3: base = 0x4908; break;
          case 4: base = 0x2000; break;
          default: return;
        }
        for (uint32_t i = 1; i < count; ++i) {
          Write(base + index + i - 1, LoadVirtual(data + 4 * i));
        }
        break;
      }
      case 0x2F: {  // LOAD_ALU_CONSTANT: constants from memory
        alu_loads_ += LoadVirtual(data + 8) & 0xFFF;
        break;
      }
      case 0x27: {  // IM_LOAD: shader microcode from memory
        const uint32_t d0 = LoadVirtual(data);
        const uint32_t dwords = LoadVirtual(data + 4) & 0xFFFF;
        Shader& s = (d0 & 3) ? ps_ : vs_;
        s.address = d0 & ~3u;
        s.dwords = dwords;
        s.hash = Hash(Mem()->TranslatePhysical<const uint8_t*>(s.address), dwords * 4);
        Head(s, Mem()->TranslatePhysical<const uint32_t*>(s.address));
        s.key = (d0 & 3) ? s.hash
                         : MaskedHash(Mem()->TranslatePhysical<const uint32_t*>(s.address), dwords);
        if (!(d0 & 3)) {
          KeepVertexShader(Mem()->TranslatePhysical<const uint32_t*>(s.address), dwords);
        }
        break;
      }
      case 0x2B: {  // IM_LOAD_IMMEDIATE: shader microcode inline
        const uint32_t d0 = LoadVirtual(data);
        const uint32_t dwords = LoadVirtual(data + 4) & 0xFFFF;
        Shader& s = (d0 & 3) ? ps_ : vs_;
        s.address = 0;
        s.dwords = dwords;
        s.hash = Hash(Mem()->TranslateVirtual<const uint8_t*>(data + 8), dwords * 4);
        Head(s, Mem()->TranslateVirtual<const uint32_t*>(data + 8));
        s.key = (d0 & 3) ? s.hash
                         : MaskedHash(Mem()->TranslateVirtual<const uint32_t*>(data + 8), dwords);
        if (!(d0 & 3)) {
          KeepVertexShader(Mem()->TranslateVirtual<const uint32_t*>(data + 8), dwords);
          // The vertex shaders D3D builds at run time (loaded inline; not in
          // the game's files): the whole microcode, once each, to write
          // their Metal versions.
          static std::set<uint64_t> logged;
          if (logged.insert(s.key).second && logged.size() <= 16) {
            std::string words;
            for (uint32_t w : vs_code_) words += fmt::format(" {:08x}", w);
            REXLOG_INFO("[d3d-vs] key {:016x} {} dw:{}", s.key, dwords, words);
          }
        }
        break;
      }
      case 0x22:  // DRAW_INDX: viz query, initiator, [index base, index size]
        initiator_ = LoadVirtual(data + 4);
        index_base_ = count > 2 ? LoadVirtual(data + 8) : 0;
        index_size_ = count > 3 ? LoadVirtual(data + 12) : 0;
        inline_draw_ = false;
        break;
      case 0x36:  // DRAW_INDX_2: initiator, inline data
        initiator_ = LoadVirtual(data);
        index_base_ = index_size_ = 0;
        inline_draw_ = true;
        break;
      default:
        break;
    }
  }

  void Write(uint32_t reg, uint32_t value) {
    if (recording_ && reg >= kRbSurfaceInfo && reg <= kRbColor1Info && regs_[reg] != value &&
        rt_writes_logged_ < 40) {
      ++rt_writes_logged_;
      lines_.push_back(fmt::format("  rt-write reg {:04x} = {:08x} by {} (draw {})", reg, value,
                                   source_, draw_index_));
    }
    if (reg < kRegisterCount) {
      regs_[reg] = value;
      if (reg >= kFetchBase && reg < kFetchBase + 32 * 6) {
        touched_.insert((reg - kFetchBase) / 6);
      } else if (reg >= kAluBase && reg < kAluBase + 512 * 4) {
        ++alu_writes_;
      }
    }
  }

  static void Head(Shader& s, const uint32_t* microcode) {
    for (uint32_t i = 0; i < 4; ++i) {
      s.head[i] = i < s.dwords ? __builtin_bswap32(microcode[i]) : 0;
    }
  }

  // The microcode's hash with its vertex fetch instructions zeroed: D3D
  // patches those when it binds a vertex shader to a vertex declaration.
  // The same walk as tools/native/nfsmw_shader_containers.py.
  static uint64_t MaskedHash(const uint32_t* microcode_be, uint32_t n) {
    std::vector<uint32_t> w(n);
    for (uint32_t i = 0; i < n; ++i) {
      w[i] = __builtin_bswap32(microcode_be[i]);
    }
    for (uint32_t i = 0; i + 2 < n; i += 3) {
      const uint64_t cfs[2] = {w[i] | (uint64_t(w[i + 1] & 0xFFFF) << 32),
                               (w[i + 1] >> 16) | (uint64_t(w[i + 2]) << 16)};
      bool stop = false;
      for (uint64_t cf : cfs) {
        const uint32_t opcode = (cf >> 44) & 0xF;
        if (opcode == 1 || opcode == 2 || (opcode >= 3 && opcode <= 6) || opcode == 13 ||
            opcode == 14) {
          const uint32_t address = cf & 0xFFF, count = (cf >> 12) & 7,
                         sequence = (cf >> 16) & 0xFFF;
          for (uint32_t k = 0; k < count; ++k) {
            const uint32_t at = (address + k) * 3;
            if (((sequence >> (2 * k)) & 1) && at + 2 < n && (w[at] & 0x1F) == 0) {
              w[at] = w[at + 1] = w[at + 2] = 0;
            }
          }
          stop |= opcode == 2 || opcode == 4 || opcode == 6 || opcode == 14;
        }
      }
      if (stop) {
        break;
      }
    }
    uint64_t h = 0xCBF29CE484222325ull;
    for (uint32_t v : w) {
      for (int b = 3; b >= 0; --b) {  // the big-endian bytes, as in the file
        h = (h ^ ((v >> (8 * b)) & 0xFF)) * 0x100000001B3ull;
      }
    }
    return h;
  }

  void KeepVertexShader(const uint32_t* microcode_be, uint32_t dwords) {
    vs_code_.resize(dwords);
    for (uint32_t i = 0; i < dwords; ++i) {
      vs_code_[i] = __builtin_bswap32(microcode_be[i]);
    }
  }

  static uint64_t Hash(const uint8_t* p, uint32_t n) {
    uint64_t h = 0xCBF29CE484222325ull;
    for (uint32_t i = 0; i < n; ++i) {
      h = (h ^ p[i]) * 0x100000001B3ull;
    }
    return h;
  }

  void Begin() {
    recording_ = true;
    lines_.clear();
    draw_index_ = 0;
    resolves_ = 0;
    pass_key_ = ~0ull;
    shaders_.clear();
    signatures_.clear();
    keys_.clear();
    rt_writes_logged_ = 0;
    textures_.clear();
    alu_writes_ = alu_loads_ = 0;
    gaps_ = 0;
    segment_switches_ = 0;
    // The state before the frame's first draw: render targets and shaders.
    lines_.push_back(fmt::format("  start: vs {:016x} ({} dw), ps {:016x} ({} dw)", vs_.hash,
                                 vs_.dwords, ps_.hash, ps_.dwords));
  }

  std::string Fetch(uint32_t slot) const {
    const uint32_t* f = &regs_[kFetchBase + slot * 6];
    if ((f[0] & 3) == 2) {  // texture
      const uint32_t format = f[1] & 0x3F;
      const uint32_t address = f[1] & ~0xFFFu;
      const bool tiled = f[0] >> 31;
      const uint32_t dimension = (f[5] >> 9) & 3;  // 1 2D, 2 3D, 3 cube
      if (dimension == 2) {  // 3D sizes: 11, 11 and 10 bits
        return fmt::format("t{}={:08x}:{}x{}x{}:f{}{}", slot, address, (f[2] & 0x7FF) + 1,
                           ((f[2] >> 11) & 0x7FF) + 1, (f[2] >> 22) + 1, format, tiled ? "T" : "");
      }
      const uint32_t width = (f[2] & 0x1FFF) + 1;
      const uint32_t height = ((f[2] >> 13) & 0x1FFF) + 1;
      rex::graphics::xenos::xe_gpu_texture_fetch_t tf;
      std::memcpy(&tf, f, sizeof(tf));
      std::string extra = fmt::format(":s{:03x}:e{}", uint32_t(tf.swizzle), uint32_t(tf.endianness));
      // DXT3 (alpha-tested foliage): the first block's raw bytes, once each.
      static std::set<uint32_t> dumped;
      if (format == 19 && dumped.size() < 4 && dumped.insert(address).second) {
        const uint8_t* b = Mem()->TranslatePhysical<const uint8_t*>(address);
        for (int i = 0; i < 16; ++i) extra += fmt::format("{}{:02x}", i ? "" : ":raw", b[i]);
      }
      return fmt::format("t{}={:08x}:{}x{}:f{}{}{}{}", slot, address, width, height, format,
                         tiled ? "T" : "", dimension == 3 ? ":cube" : "", extra);
    }
    std::string s;
    for (int v = 0; v < 3; ++v) {  // three vertex fetches per slot
      const uint32_t* vf = f + v * 2;
      if ((vf[0] & 3) == 3) {
        s += fmt::format("{}v{}={:08x}+{}", s.empty() ? "" : " ", slot * 3 + v, vf[0] & ~3u,
                         ((vf[1] >> 2) & 0xFFFFFF) * 4);
      }
    }
    return s;
  }

  void Record(Kind kind, uint32_t primitive, uint32_t count) {
    const uint32_t surface = regs_[kRbSurfaceInfo], color = regs_[kRbColorInfo],
                   depth = regs_[kRbDepthInfo], color1 = regs_[kRbColor1Info];
    const uint64_t key = (uint64_t(surface) << 32) ^ (uint64_t(color) << 16) ^ depth ^
                         (uint64_t(color1) << 8);
    if (key != pass_key_) {
      pass_key_ = key;
      // pitch, msaa; color edram base and format; depth base and format.
      lines_.push_back(fmt::format(
          "  == pass: pitch {} msaa {}x, color base {} fmt {}, color1 {:08x}, depth base {} "
          "fmt {} (raw 2000-2003: {:08x} {:08x} {:08x} {:08x})",
          surface & 0x3FFF, 1u << ((surface >> 16) & 3), color & 0xFFF, (color >> 16) & 0xF,
          color1, depth & 0xFFF, (depth >> 16) & 1, surface, color, depth, color1));
    }
    shaders_.insert({vs_.hash, ps_.hash});
    keys_.insert({vs_.key, ps_.key});
    for (const Shader* s : {&vs_, &ps_}) {
      if (signatures_.emplace(s->hash, *s).second) {
        lines_.push_back(fmt::format(
            "  shader {:016x} {} {} dw at {:08x}: {:08x} {:08x} {:08x} {:08x} key {:016x}", s->hash,
            s == &vs_ ? "vs" : "ps", s->dwords, s->address, s->head[0], s->head[1], s->head[2],
            s->head[3], s->key));
      }
    }
    // Every texture slot the draw can see (0-15), not only those it set:
    // state set by earlier draws is what the shader reads too. Then the
    // vertex fetches this draw set.
    std::string fetches;
    for (uint32_t slot = 0; slot < 16; ++slot) {
      if ((regs_[kFetchBase + slot * 6] & 3) == 2) {
        fetches += " " + Fetch(slot);
        textures_.insert(regs_[kFetchBase + slot * 6 + 1] & ~0xFFFu);
      }
    }
    for (uint32_t slot : touched_) {
      if ((regs_[kFetchBase + slot * 6] & 3) == 2) continue;  // listed above
      const std::string f = Fetch(slot);
      if (!f.empty()) {
        fetches += " " + f;
        if ((regs_[kFetchBase + slot * 6] & 3) == 2) {
          textures_.insert(regs_[kFetchBase + slot * 6 + 1] & ~0xFFFu);
        }
      }
    }
    lines_.push_back(fmt::format(
        "  d{} {} prim {} n {} vs {:016x} ps {:016x} z {:08x} blend {:08x} cc {:08x} mode {:08x} "
        "mask {:x} sq {:08x} init {:08x} ib {:08x} aref {:.3f}{}",
        draw_index_, kind == kIndexed ? "I" : kind == kInline ? "U" : kind == kOther1 ? "D1" : kind == kOther2 ? "D2" : "D", primitive, count,
        vs_.key, ps_.hash, regs_[kRbDepthControl], regs_[kRbBlendControl0],
        regs_[kRbColorControl], regs_[kPaSuScModeCntl], regs_[kRbColorMask],
        regs_[kSqProgramCntl], initiator_, index_base_, [&] {
          float f;
          std::memcpy(&f, &regs_[0x210E], 4);  // RB_ALPHA_REF
          return f;
        }(), fetches));
    ++draw_index_;
  }

  void Flush() {
    REXLOG_INFO("[draw-capture] frame: {} draws, {} resolves, {} shader pairs, {} textures, {} "
                "ALU constant dwords written + {} loaded, {} ring gaps, {} segment switches",
                draw_index_, resolves_, shaders_.size(), textures_.size(), alu_writes_,
                alu_loads_, gaps_, segment_switches_);
    for (const std::string& line : lines_) {
      REXLOG_INFO("[draw-capture]{}", line);
    }
    REXLOG_INFO("[draw-capture] end of frame");
    std::vector<uint64_t> pairs;
    for (const auto& [vs, ps] : keys_) {
      pairs.push_back(vs);
      pairs.push_back(ps);
    }
    nfsmw_native_probe_pipelines(pairs.data(), uint32_t(keys_.size()));
  }

  std::vector<uint32_t> regs_ = std::vector<uint32_t>(kRegisterCount);
  std::vector<uint32_t> saved_regs_;  // the register file before a resolve
  bool in_call_ = false;              // inside a hooked draw or resolve
  NfsmwNativeDraw pending_{};         // a DrawPrimitiveUP waiting for its vertices
  bool has_pending_ = false;
  uint32_t segment_switches_ = 0;
  std::set<uint32_t> touched_;  // fetch slots written by the current draw
  Shader vs_, ps_;
  uint32_t initiator_ = 0, index_base_ = 0, index_size_ = 0;
  bool inline_draw_ = false;
  std::vector<uint32_t> vs_code_;  // the bound vertex shader (host byte order)
  bool native_frame_ = false;      // the native renderer records this frame
  uint32_t before_ = 0, last_after_ = 0;

  bool recording_ = false;
  int64_t next_ms_ = 0;
  std::vector<std::string> lines_;
  uint32_t draw_index_ = 0, resolves_ = 0, gaps_ = 0;
  uint64_t alu_writes_ = 0, alu_loads_ = 0;
  uint64_t pass_key_ = ~0ull;
  std::set<std::pair<uint64_t, uint64_t>> shaders_;
  std::map<uint64_t, Shader> signatures_;
  std::set<std::pair<uint64_t, uint64_t>> keys_;  // (VS key, PS hash) pairs
  std::string source_;                            // the packet being decoded
  uint32_t rt_writes_logged_ = 0;
  std::set<uint32_t> textures_;
};

// One thread issues the game's draws; the capture follows only that one.
Capture capture;
std::atomic<std::thread::id> capture_thread{};
// The device the plain and indexed draws pass; other hooks are only decoded
// when they pass the same one (their r3 has not been proven to be the device).
std::atomic<uint32_t> known_device{0};

// The thread that last called Swap: the menu and the races draw from
// different threads.
}  // namespace
// The native renderer takes its draws from the command processor
// (native_renderer.mm, nfsmw_native_cp): then this capture stays out of the
// game's thread.
extern "C" bool nfsmw_native_cp_mode();
namespace {

bool Capturing() {
  return REXCVAR_GET(nfsmw_draw_capture) && !nfsmw_native_cp_mode() && rex::system::kernel_state() &&
         capture_thread.load(std::memory_order_relaxed) == std::this_thread::get_id();
}

}  // namespace

// Game-thread time in the capture (decoding the command stream, and the
// recording it calls), for the native renderer's log.
std::atomic<uint64_t> nfsmw_capture_ns{0};
namespace {
struct CaptureTimer {
  std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
  ~CaptureTimer() {
    nfsmw_capture_ns += uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                     std::chrono::steady_clock::now() - start).count());
  }
};
}  // namespace

#define NFSMW_DRAW_HOOK(addr, kind, count_reg)                                          \
  extern "C" REX_FUNC(sub_##addr) {                                                     \
    const uint32_t device = ctx.r3.u32, primitive = ctx.r4.u32,                         \
                   count = ctx.count_reg.u32, start = ctx.r5.u32;                       \
    if (REXCVAR_GET(nfsmw_draw_census)) {                                               \
      Count(kind, device, primitive, count);                                            \
    }                                                                                   \
    if (kind == kDraw || kind == kIndexed) {                                            \
      known_device.store(device, std::memory_order_relaxed);                            \
    }                                                                                   \
    const bool capturing =                                                              \
        device && device == known_device.load(std::memory_order_relaxed) && Capturing(); \
    if (capturing) {                                                                    \
      CaptureTimer timer;                                                               \
      capture.Before(device);                                                           \
    }                                                                                   \
    __imp__sub_##addr(ctx, base);                                                       \
    if (capturing) {                                                                    \
      CaptureTimer timer;                                                               \
      capture.After(kind, device, primitive, count, start, ctx.r3.u32);                 \
    }                                                                                   \
  }

NFSMW_DRAW_HOOK(82593818, kDraw, r6)
NFSMW_DRAW_HOOK(82593A58, kIndexed, r7)
// sub_825930E0 is D3D's draw from user memory (DrawPrimitiveUP): (device,
// primitive, vertex count r5, vertex stride r6); it reserves the vertices'
// space in the command buffer and returns it: the caller (e.g. the wrapper
// sub_82593390) copies the vertices in after it returns.
NFSMW_DRAW_HOOK(825930E0, kOther1, r5)
NFSMW_DRAW_HOOK(82593408, kOther2, r6)
NFSMW_DRAW_HOOK(8259A308, kInline, r6)

extern "C" REX_FUNC(sub_82592340) {
  if (REXCVAR_GET(nfsmw_draw_census)) {
    Count(kResolve, ctx.r3.u32, 0, 0);
  }
  // Its device is the draws' (r3); only then are its packets decoded.
  const uint32_t device = ctx.r3.u32;
  const bool capturing =
      device && device == known_device.load(std::memory_order_relaxed) && Capturing();
  if (capturing) {
    capture.ResolveBefore(device);
  }
  __imp__sub_82592340(ctx, base);
  if (capturing) {
    CaptureTimer timer;
    capture.Resolve(device);
  }
}

extern "C" void __imp__sub_82597070(PPCContext& __restrict ctx, uint8_t* base);
// D3D's "make space": a new command buffer segment (returns the new write
// pointer, the last dword written).
extern "C" REX_FUNC(sub_82597070) {
  const uint32_t device = ctx.r3.u32;
  const bool capturing =
      device && device == known_device.load(std::memory_order_relaxed) && Capturing();
  if (capturing) {
    capture.SegmentSwitchBefore(device);
  }
  __imp__sub_82597070(ctx, base);
  if (capturing) {
    capture.SegmentSwitchAfter(ctx.r3.u32);
  }
}

extern "C" REX_FUNC(sub_825987E0) {
  if (REXCVAR_GET(nfsmw_draw_capture) && !nfsmw_native_cp_mode() && rex::system::kernel_state()) {
    const std::thread::id self = std::this_thread::get_id();
    if (capture_thread.exchange(self) == self) {
      capture.Swap();
    }
  }
  __imp__sub_825987E0(ctx, base);
}
