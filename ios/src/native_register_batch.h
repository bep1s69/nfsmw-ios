// Owned register deltas only; no guest pointers survive publication.
#pragma once
#include <array>
#include <atomic>
#include <bit>
#include <cstdint>
#include <cstring>
#include <limits>
#include <span>
#include <utility>

namespace nfsmw::register_batch {
inline constexpr uint32_t kMagic=0x4E465242, kVersion=1, kHeader=0xC0031000;
inline constexpr uint32_t kRegisters=0x6000, kWords=1024, kRuns=32;
struct Run { uint32_t reg, count, offset; };
struct Site {uint32_t lr,reg,offset,words,group;};
inline constexpr Site kSites[]={
  {0x825A3F38,0x2300,11768,38,1},{0x825A3F5C,0x2380,11920,8,1},
  {0x825A3F80,0x4000,1920,1024,16},{0x825A3FA4,0x4400,6016,1024,16},
  {0x825A3FFC,0x4900,10112,40,1},{0x825A4020,0x2000,11456,16,1},
  {0x825A404C,0x2100,11532,21,1},{0x825A4078,0x2180,11616,5,1},
  {0x825A40A4,0x2200,11636,12,1},{0x825A40C8,0x2280,11684,21,1}};
inline const Site* FindSite(uint32_t lr,uint32_t reg,uint32_t source,uint32_t device,uint32_t group) {
  if(!device || (device&3))return nullptr;
  for(const auto& site:kSites)if(site.lr==lr && site.reg==reg && site.group==group &&
      device<=UINT32_MAX-site.offset-site.words*4 && source==device+site.offset &&
      (group!=16 || !(source&15)))return &site;
  return nullptr;
}
struct Batch {
  std::array<Run,kRuns> runs;
  std::array<uint32_t,kWords> words; // raw BE bytes, CP performs existing swap
  uint32_t run_count=0, word_count=0;
  bool Valid() const {
    if (!run_count || run_count>kRuns || !word_count || word_count>kWords) return false;
    uint32_t at=0,last=0;
    for (uint32_t i=0;i<run_count;++i) {
      const auto& r=runs[i];
      if (!r.count || r.reg<last || r.reg>=kRegisters || r.count>kRegisters-r.reg ||
          r.offset!=at || r.count>word_count-at) return false;
      at+=r.count; last=r.reg+r.count;
    }
    return at==word_count;
  }
};
// Bounds validated before touching output. Dirty mask is MSB-first; grouped
// emitter bits represent sixteen words, not one float4.
inline bool Build(Batch& out,uint64_t mask,uint32_t reg,uint32_t group,
                  std::span<const uint32_t> source) {
  if (!mask || (group!=1 && group!=16) || reg>=kRegisters) return false;
  const uint32_t needed=(64-std::countr_zero(mask))*group;
  if (needed>source.size() || needed>kRegisters-reg) return false;
  out.run_count=out.word_count=0;
  while(mask) {
    const uint32_t first=std::countl_zero(mask), count=std::countl_one(mask<<first);
    const uint32_t words=count*group, offset=first*group;
    out.runs[out.run_count++]={reg+offset,words,out.word_count};
    std::memcpy(out.words.data()+out.word_count,source.data()+offset,words*4);
    out.word_count+=words;
    const uint32_t end=first+count;
    mask=end==64 ? 0 : mask & (UINT64_MAX>>end);
  }
  return true;
}
// Prove the ORIGINAL emitter would stay entirely on its fast path, including
// grouped filler stores. Preserve its ending mod16 alignment for later users.
inline uint32_t OriginalEnd(uint32_t last,uint32_t limit,uint64_t mask,uint32_t group) {
  if (!mask || (last&3) || (limit&3) || last>=limit || (group!=1 && group!=16)) return 0;
  uint64_t at=last;
  while(mask) {
    const uint32_t first=std::countl_zero(mask), count=std::countl_one(mask<<first);
    const uint32_t words=count*group;
    if (at+uint64_t(words+(group==16?3:0))*4>=limit) return 0;
    if(group==16) at+=(uint64_t(-8)-at)&15;
    at+=uint64_t(words+1)*4;
    const uint32_t end=first+count;
    mask=end==64 ? 0 : mask & (UINT64_MAX>>end);
  }
  return uint32_t(at);
}
inline uint32_t TokenEnd(uint32_t last,uint32_t original_end) {
  const uint64_t end=uint64_t(last)+20;
  const uint64_t padded=end+((uint64_t(original_end)-end)&15);
  return padded<=original_end ? uint32_t(padded) : 0;
}

// Bounded independent slots. Producers never wait for consumers or reuse live
// records. Tickets are unique until exhaustion; wrap disables reservations.
template<size_t Slots> class Pool {
  static_assert(std::has_single_bit(Slots));
  static constexpr unsigned kBits=std::countr_zero(Slots);
  static constexpr uint64_t kWriting=UINT64_MAX,kReading=UINT64_MAX-1;
  struct Slot { std::atomic<uint64_t> state{0}; Batch batch; };
 public:
  class Reservation {
   public:
    Reservation()=default;
    Reservation(const Reservation&)=delete;
    Reservation& operator=(const Reservation&)=delete;
    Reservation(Reservation&& other) noexcept : slot_(std::exchange(other.slot_,nullptr)),ticket_(other.ticket_) {}
    ~Reservation(){if(slot_)slot_->state.store(0,std::memory_order_release);}
    explicit operator bool()const{return slot_!=nullptr;}
    Batch& Data(){return slot_->batch;}
    uint64_t Publish() {
      if(!slot_ || !slot_->batch.Valid())return 0;
      slot_->state.store(ticket_,std::memory_order_release);
      slot_=nullptr;return ticket_;
    }
   private:
    friend class Pool;
    Reservation(Slot* slot,uint64_t ticket):slot_(slot),ticket_(ticket){}
    Slot* slot_=nullptr;
    uint64_t ticket_=0;
  };
  explicit Pool(uint64_t initial=1):next_(initial){}
  Reservation Reserve() {
    // Saturate instead of wrapping even when several producer threads contend.
    uint64_t seq=next_.load(std::memory_order_relaxed);
    do {if(!seq || seq>((UINT64_MAX>>kBits)-2))return {};}
    while(!next_.compare_exchange_weak(seq,seq+1,std::memory_order_relaxed));
    constexpr size_t probes=Slots<8?Slots:8;
    for(size_t n=0;n<probes;++n) {
      const size_t index=(seq+n)&(Slots-1);
      uint64_t free=0;
      if(slots_[index].state.compare_exchange_strong(free,kWriting,std::memory_order_acquire)) {
        slots_[index].batch.run_count=slots_[index].batch.word_count=0;
        return Reservation(&slots_[index],(seq<<kBits)|index);
      }
    }
    return {}; // no nearby free slot; safe original-writer fallback, not a wait
  }
  template<class Write> bool Consume(uint64_t ticket,Write&& write) {
    if(!ticket || ticket>=kReading)return false;
    auto& slot=slots_[ticket&(Slots-1)];uint64_t ready=ticket;
    if(!slot.state.compare_exchange_strong(ready,kReading,std::memory_order_acquire))return false;
    struct Release {Slot& slot;~Release(){slot.state.store(0,std::memory_order_release);}} release{slot};
    if(!slot.batch.Valid())return false;
    for(uint32_t i=0;i<slot.batch.run_count;++i) {
      const auto& r=slot.batch.runs[i];
      write(r.reg,slot.batch.words.data()+r.offset,r.count);
    }
    return true;
  }
 private:
  std::array<Slot,Slots> slots_;
  std::atomic<uint64_t> next_;
};
} // namespace nfsmw::register_batch
