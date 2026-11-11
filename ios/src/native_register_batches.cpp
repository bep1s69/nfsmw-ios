// C0/C1: dirty state takes an owned host route; draws and all other operations
// still pass through the original ordered CP/Record path. USA callsites only.
#include "nfsmw_pch.h"
#include "native_register_batch.h"
#include <rex/cvar.h>
#include <rex/logging.h>
#include <new>
#include <cstdlib>
#include <optional>
REXCVAR_DECLARE(std::string,gpu_backend);

REXCVAR_DEFINE_BOOL(nfsmw_native_register_batches,false,"GPU",
                   "Trial: owned dirty-register batches at proved USA flush calls (restart required)");
REXCVAR_DEFINE_BOOL(nfsmw_native_register_flushes,false,"GPU",
                   "Trial: aggregate compatible USA state-flush updates (restart required)");
using RexNativeRegisterWrite=void (*)(void*,uint32_t,uint32_t*,uint32_t);
using RexNativeRegisterBatch=bool (*)(uint64_t,RexNativeRegisterWrite,void*);
extern std::atomic<RexNativeRegisterBatch> rex_native_register_batch_hook;
extern "C" bool nfsmw_native_cp_mode();
extern "C" void __imp__sub_825A28A8(PPCContext&,uint8_t*);
extern "C" void __imp__sub_825A2A60(PPCContext&,uint8_t*);
extern "C" void __imp__sub_825A2968(PPCContext&,uint8_t*);
extern "C" void __imp__sub_825A3EC8(PPCContext&,uint8_t*);
namespace {
using namespace nfsmw::register_batch;
using Batches=Pool<2048>;
Batches* Storage(){static auto* pool=new(std::nothrow) Batches;return pool;}
bool Enabled(){static const bool on=REXCVAR_GET(nfsmw_native_register_batches);return on;}
bool FlushEnabled(){static const bool on=REXCVAR_GET(nfsmw_native_register_flushes);return on;}
struct Stats {
  std::atomic<uint64_t> produced{0},consumed{0},words{0},runs{0},old_bytes{0},new_bytes{0};
  std::atomic<uint64_t> unsupported{0},small{0},boundary{0},capacity{0},pending{0},peak{0};
  std::atomic<uint64_t> flushes{0},collected{0},sparse{0};
} stats;
void Add(std::atomic<uint64_t>& value,uint64_t n=1){value.fetch_add(n,std::memory_order_relaxed);}
bool Consume(uint64_t ticket,RexNativeRegisterWrite write,void* opaque) {
  auto* pool=Storage();
  if(!pool || !write)return false;
  const bool done=pool->Consume(ticket,[&](uint32_t reg,uint32_t* data,uint32_t count){write(opaque,reg,data,count);});
  if(done){stats.consumed.fetch_add(1,std::memory_order_relaxed);stats.pending.fetch_sub(1,std::memory_order_relaxed);}
  return done;
}
void Publish(Batches::Reservation& lease,uint8_t* base,uint32_t device,uint32_t last,uint32_t original_end) {
  const uint32_t token_end=TokenEnd(last,original_end);
  if(!token_end || !lease.Data().Valid())std::abort();
  const uint64_t words=lease.Data().word_count,runs=lease.Data().run_count;
  const uint64_t pending=stats.pending.fetch_add(1,std::memory_order_relaxed)+1;
  uint64_t peak=stats.peak.load(std::memory_order_relaxed);
  while(peak<pending&&!stats.peak.compare_exchange_weak(peak,pending,std::memory_order_relaxed)){}
  const uint64_t ticket=lease.Publish(); // validated above; immutable before token
  if(!ticket)std::abort();
  // The guest ring uses its own (non-C++-atomic) publication protocol. Order
  // Ready globally before ordinary ring stores, not just before an acquire of
  // the slot that a consumer might attempt as soon as it sees the token.
  std::atomic_thread_fence(std::memory_order_release);
  REX_STORE_U32(last+4,kHeader);REX_STORE_U32(last+8,kMagic);REX_STORE_U32(last+12,kVersion);
  REX_STORE_U32(last+16,uint32_t(ticket));REX_STORE_U32(last+20,uint32_t(ticket>>32));
  for(uint32_t at=last+24;at<=token_end;at+=4)REX_STORE_U32(at,0x80000000u);
  REX_STORE_U32(device,token_end);
  Add(stats.produced);Add(stats.words,words);Add(stats.runs,runs);
  Add(stats.old_bytes,original_end-last);Add(stats.new_bytes,token_end-last);
}
bool Try(PPCContext& ctx,uint8_t* base,uint32_t group) {
  if(!Enabled())return false;
  // The original VMX writer is already cheap for small constant runs. Host
  // crossover tests reject those instead of expanding them into pool work.
  const unsigned words_set=std::popcount(ctx.r4.u64)*group;
  if(words_set<(group==16?256u:32u)){Add(stats.small);return false;}
  if(rex_native_register_batch_hook.load(std::memory_order_acquire)!=&Consume)return false;
  // Do not mix with the old game-thread capture/decoder or a Vulkan backend.
  if(!nfsmw_native_cp_mode() || REXCVAR_GET(gpu_backend)!="native")return false;
  const auto* site=FindSite(uint32_t(ctx.lr),ctx.r5.u32,ctx.r6.u32,ctx.r3.u32,group);
  if(!site || !ctx.r4.u64){Add(stats.unsupported);return false;}
  // A contiguous raw copy must not straddle the guest's high-physical alias
  // skew. Each original scalar/VMX access uses REX_RAW_ADDR's host mapping.
  const uint32_t source_last=ctx.r6.u32+site->words*4-1;
  if((ctx.r6.u32>=0xE0000000u)!=(source_last>=0xE0000000u)){
    Add(stats.unsupported);return false;
  }
  const uint32_t needed=(64-std::countr_zero(ctx.r4.u64))*group;
  if(needed>site->words){Add(stats.unsupported);return false;}
  const uint32_t device=ctx.r3.u32;
  const uint32_t last=REX_LOAD_U32(device),limit=REX_LOAD_U32(device+4);
  const uint32_t original_end=OriginalEnd(last,limit,ctx.r4.u64,group);
  const uint32_t token_end=original_end?TokenEnd(last,original_end):0;
  const bool overlaps=uint64_t(last)+4<uint64_t(device)+site->offset+site->words*4 && token_end>=device;
  if(!token_end || overlaps || (last<0xE0000000u && original_end>=0xE0000000u)){
    Add(stats.boundary);return false;
  }
  // All fallback decisions precede publication and any guest writes. No segment
  // rollover, no dirty-mask edits, no new guest memory reads after the token.
  auto* pool=Storage();if(!pool){Add(stats.capacity);return false;}
  auto lease=pool->Reserve();if(!lease){Add(stats.capacity);return false;}
  const auto* source=reinterpret_cast<const uint32_t*>(REX_RAW_ADDR(ctx.r6.u32));
  if(!Build(lease.Data(),ctx.r4.u64,site->reg,group,{source,site->words})){
    Add(stats.unsupported);return false;
  }
  Publish(lease,base,device,last,original_end);
  return true;
}
// Fetch's generated writer aligns its header to 8 bytes differently from VMX.
inline uint32_t FetchEnd(uint32_t last,uint32_t limit,uint64_t mask) {
  if(!mask || (last&3) || (limit&3) || last>=limit)return 0;
  uint64_t at=last;
  while(mask) {
    unsigned first=std::countl_zero(mask),count=std::countl_one(mask<<first);
    if(at+uint64_t(count*6+1)*4>=limit)return 0;
    at+=(at&7)+uint64_t(count*6+1)*4;
    unsigned end=first+count;mask=end==64?0:mask&(UINT64_MAX>>end);
  }
  return uint32_t(at);
}
struct Collector {
  uint8_t* base;
  uint32_t device;
  std::optional<Batches::Reservation> lease;
  uint32_t first=0,end=0,limit=0;
  unsigned packets=0;
  explicit Collector(uint8_t* memory,uint32_t dev):base(memory),device(dev){}
  void Flush() {
    if(!lease)return;
    // The audited suffix contains no ring publisher/foreign writer between
    // these calls. Such a new observer must get an explicit BEFORE-call
    // barrier; detecting it after its writes cannot safely replay this prefix.
    if(REX_LOAD_U32(device)!=first || REX_LOAD_U32(device+4)!=limit)std::abort();
    if(!TokenEnd(first,end))std::abort();
    Publish(*lease,base,device,first,end);lease.reset();
  }
  // Returning false means flush a collected PREFIX, then run the CURRENT
  // original writer. Never rerun a prefix or roll back CPU-visible effects.
  bool AddCall(PPCContext& ctx,uint32_t group) {
    static constexpr Site fetch={0x825A3FD0,0x4800,1152,192,6};
    const Site* site=FindSite(uint32_t(ctx.lr),ctx.r5.u32,ctx.r6.u32,ctx.r3.u32,group);
    if(group==6 && uint32_t(ctx.lr)==fetch.lr && ctx.r5.u32==fetch.reg &&
        device<=UINT32_MAX-fetch.offset-fetch.words*4 && ctx.r6.u32==device+fetch.offset)site=&fetch;
    if(!site || ctx.r3.u32!=device || !ctx.r4.u64 || (device&3) ||
        device>UINT32_MAX-12000 ||
        (64-std::countr_zero(ctx.r4.u64))*group>site->words ||
        ((ctx.r6.u32>=0xE0000000u)!=((ctx.r6.u32+site->words*4-1)>=0xE0000000u))) {
      Add(stats.unsupported);Flush();return false;
    }
    auto prepare=[&] {
      uint32_t last=lease?end:REX_LOAD_U32(device);
      uint32_t bound=REX_LOAD_U32(device+4);
      uint32_t next=group==6?FetchEnd(last,bound,ctx.r4.u64):OriginalEnd(last,bound,ctx.r4.u64,group);
      uint32_t start=lease?first:last;
      // Ring must not alias ANY device state, including later source banks and
      // dirty masks. Keep the original high-physical mapping discontinuity out.
      if(!next || !TokenEnd(start,next) ||
          (uint64_t(start)+4<uint64_t(device)+12000 && next>=device) ||
          (start<0xE0000000u && next>=0xE0000000u) ||
          (lease && (bound!=limit || REX_LOAD_U32(device)!=first))){Add(stats.boundary);return false;}
      const auto* source=reinterpret_cast<const uint32_t*>(REX_RAW_ADDR(ctx.r6.u32));
      if(!lease) {
        auto* pool=Storage();if(!pool){Add(stats.capacity);return false;}
        lease.emplace(pool->Reserve());if(!*lease){lease.reset();Add(stats.capacity);return false;}
        first=last;limit=bound;
      }
      if(!Append(lease->Data(),ctx.r4.u64,site->reg,group,{source,site->words})) {
        // No partial append occurred; flush immutable old prefix before trying
        // this call at the new actual ring pointer.
        Add(stats.capacity);if(!lease->Data().word_count)lease.reset();
        return false;
      }
      end=next;++packets;return true;
    };
    if(prepare())return true;
    Flush();
    return prepare(); // one bounded retry after capacity/space barrier
  }
};
thread_local Collector* active=nullptr;
struct SuspendCollector {
  Collector* saved=std::exchange(active,nullptr);
  ~SuspendCollector(){active=saved;}
};

// This is only an admission estimate. Prefix helpers may dirty more state;
// exact roles, snapshots and boundaries are still checked at every emitter.
bool WorthCollecting(uint8_t* base,uint32_t device) {
  if(!device || (device&3) || device>UINT32_MAX-12000)return false;
  const uint64_t vs=REX_LOAD_U64(device+16),ps=REX_LOAD_U64(device+24);
  const uint64_t fetch=REX_LOAD_U64(device+32),scalar=REX_LOAD_U64(device+40),misc=REX_LOAD_U64(device+48);
  const unsigned words=(std::popcount(vs)+std::popcount(ps))*16+
    std::popcount(fetch&0xFFFFFFFF00000000ull)*6+((fetch&0x80000000)?40:0)+
    std::popcount(fetch&0x3FFFC000)+std::popcount(scalar&~31ull)+
    std::popcount(misc&~0x3FFFFull);
  const unsigned calls=bool(vs)+bool(ps)+bool(fetch&0xFFFFFFFF00000000ull)+
    bool(fetch&0x80000000)+bool(fetch&0x3FFFC000)+bool(scalar&~31ull)+bool(misc&~0x3FFFFull);
  return words>=128 && calls>=2;
}
__attribute__((constructor)) void Install(){rex_native_register_batch_hook.store(&Consume,std::memory_order_release);}
} // namespace
extern "C" REX_FUNC(sub_825A28A8){
  if(active){if(!active->AddCall(ctx,1)){SuspendCollector suspended;__imp__sub_825A28A8(ctx,base);}return;}
  if(!Try(ctx,base,1))__imp__sub_825A28A8(ctx,base);
}
extern "C" REX_FUNC(sub_825A2A60){
  if(active){if(!active->AddCall(ctx,16)){SuspendCollector suspended;__imp__sub_825A2A60(ctx,base);}return;}
  if(!Try(ctx,base,16))__imp__sub_825A2A60(ctx,base);
}
extern "C" REX_FUNC(sub_825A2968){
  if(active){
    if(active->AddCall(ctx,6))return;
    SuspendCollector suspended;__imp__sub_825A2968(ctx,base);return;
  }
  __imp__sub_825A2968(ctx,base);
}
extern "C" REX_FUNC(sub_825A3EC8){
  if(!FlushEnabled() && !active){__imp__sub_825A3EC8(ctx,base);return;}
  // Even a sparse nested flush is an ordering barrier for its parent.
  if(active)active->Flush();SuspendCollector suspended;
  if(!FlushEnabled() || rex_native_register_batch_hook.load(std::memory_order_acquire)!=&Consume ||
      !nfsmw_native_cp_mode() || REXCVAR_GET(gpu_backend)!="native" ) {
    __imp__sub_825A3EC8(ctx,base);return;
  }
  if(!WorthCollecting(base,ctx.r3.u32)){Add(stats.sparse);__imp__sub_825A3EC8(ctx,base);return;}
  Collector collector(base,ctx.r3.u32);active=&collector;
  // Normal generated code does not throw. Keep the TLS owner and collected
  // prefix valid during host exception unwinding as well.
  try {__imp__sub_825A3EC8(ctx,base);collector.Flush();}
  catch(...) {collector.Flush();throw;}
  Add(stats.flushes);Add(stats.collected,collector.packets);
}
extern "C" bool nfsmw_register_flushes_enabled(){return FlushEnabled();}
extern "C" bool nfsmw_register_batches_enabled(){return Enabled();}
extern "C" void nfsmw_register_batches_report() {
  if(!Enabled() && !FlushEnabled())return;
  static unsigned frames=0;if(++frames<300)return;frames=0;
  REXLOG_INFO("[register-batches] dev123 300 frames: {} produced / {} consumed, {} words / {} runs; "
              "original {} bytes / token {} bytes; fallback unsupported {} small {} boundary {} capacity {}; "
              "{} pending / {} peak; pool {} KiB; flushes {} / collected calls {} / sparse {} (activity, not CPU or energy savings)",
    stats.produced.exchange(0),stats.consumed.exchange(0),stats.words.exchange(0),stats.runs.exchange(0),
    stats.old_bytes.exchange(0),stats.new_bytes.exchange(0),stats.unsupported.exchange(0),stats.small.exchange(0),
    stats.boundary.exchange(0),stats.capacity.exchange(0),stats.pending.load(),stats.peak.load(),sizeof(Batches)/1024,stats.flushes.exchange(0),stats.collected.exchange(0),stats.sparse.exchange(0));
}
