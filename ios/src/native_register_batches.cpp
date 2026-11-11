// C0: dirty state takes an owned host route; draws and all other operations
// still pass through the original ordered CP/Record path. USA callsites only.
#include "nfsmw_pch.h"
#include "native_register_batch.h"
#include <rex/cvar.h>
#include <rex/logging.h>
#include <new>
#include <cstdlib>
REXCVAR_DECLARE(std::string,gpu_backend);

REXCVAR_DEFINE_BOOL(nfsmw_native_register_batches,false,"GPU",
                   "Trial: owned dirty-register batches at proved USA flush calls (restart required)");
using RexNativeRegisterWrite=void (*)(void*,uint32_t,uint32_t*,uint32_t);
using RexNativeRegisterBatch=bool (*)(uint64_t,RexNativeRegisterWrite,void*);
extern std::atomic<RexNativeRegisterBatch> rex_native_register_batch_hook;
extern "C" bool nfsmw_native_cp_mode();
extern "C" void __imp__sub_825A28A8(PPCContext&,uint8_t*);
extern "C" void __imp__sub_825A2A60(PPCContext&,uint8_t*);
namespace {
using namespace nfsmw::register_batch;
using Batches=Pool<2048>;
Batches* Storage(){static auto* pool=new(std::nothrow) Batches;return pool;}
bool Enabled(){static const bool on=REXCVAR_GET(nfsmw_native_register_batches);return on;}
struct Stats {
  std::atomic<uint64_t> produced{0},consumed{0},words{0},runs{0},old_bytes{0},new_bytes{0};
  std::atomic<uint64_t> unsupported{0},small{0},boundary{0},capacity{0},pending{0},peak{0};
} stats;
void Add(std::atomic<uint64_t>& value,uint64_t n=1){value.fetch_add(n,std::memory_order_relaxed);}
bool Consume(uint64_t ticket,RexNativeRegisterWrite write,void* opaque) {
  auto* pool=Storage();
  if(!pool || !write)return false;
  const bool done=pool->Consume(ticket,[&](uint32_t reg,uint32_t* data,uint32_t count){write(opaque,reg,data,count);});
  if(done){stats.consumed.fetch_add(1,std::memory_order_relaxed);stats.pending.fetch_sub(1,std::memory_order_relaxed);}
  return done;
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
  return true;
}
__attribute__((constructor)) void Install(){rex_native_register_batch_hook.store(&Consume,std::memory_order_release);}
} // namespace
extern "C" REX_FUNC(sub_825A28A8){if(!Try(ctx,base,1))__imp__sub_825A28A8(ctx,base);}
extern "C" REX_FUNC(sub_825A2A60){if(!Try(ctx,base,16))__imp__sub_825A2A60(ctx,base);}
extern "C" bool nfsmw_register_batches_enabled(){return Enabled();}
extern "C" void nfsmw_register_batches_report() {
  if(!Enabled())return;
  static unsigned frames=0;if(++frames<300)return;frames=0;
  REXLOG_INFO("[register-batches] dev122 300 frames: {} produced / {} consumed, {} words / {} runs; "
              "original {} bytes / token {} bytes; fallback unsupported {} small {} boundary {} capacity {}; "
              "{} pending / {} peak; pool {} KiB (activity, not CPU or energy savings)",
    stats.produced.exchange(0),stats.consumed.exchange(0),stats.words.exchange(0),stats.runs.exchange(0),
    stats.old_bytes.exchange(0),stats.new_bytes.exchange(0),stats.unsupported.exchange(0),stats.small.exchange(0),
    stats.boundary.exchange(0),stats.capacity.exchange(0),stats.pending.load(),stats.peak.load(),sizeof(Batches)/1024);
}
