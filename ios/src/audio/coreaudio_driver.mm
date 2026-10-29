// NFSMW Recompiled - audio output on iOS (see coreaudio_driver.h)

#include "coreaudio_driver.h"

#import <AVFoundation/AVFoundation.h>
#include <AudioToolbox/AudioToolbox.h>

#include <SDL3/SDL_events.h>

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/system/xmemory.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <mutex>

#include <pthread.h>
#include <time.h>

#include "../boot_trace.h"

// The launcher's "Play sound in silent mode" (Audio tab).
REXCVAR_DEFINE_BOOL(ios_audio_silent_mode, false, "Audio",
                    "Play the game's sound with the phone's silent switch on (Playback session category)");

namespace rex::audio::ios {

namespace {

constexpr double kSampleRate = 48000.0;

// 5.1 to stereo fold weights (the same as the Android driver).
constexpr float kCenterGain = 0.7071f;
constexpr float kSurroundGain = 0.7071f;
constexpr float kLfeGain = 0.5f;

inline float LoadBEFloat(uint32_t raw_be) {
  const uint32_t le = __builtin_bswap32(raw_be);
  float f;
  std::memcpy(&f, &le, sizeof(float));
  return f;
}

OSStatus RenderCallback(void* ref, AudioUnitRenderActionFlags* /*flags*/,
                        const AudioTimeStamp* /*time*/, UInt32 /*bus*/, UInt32 frames,
                        AudioBufferList* data) {
  auto* self = static_cast<CoreAudioDriver*>(ref);
  // One interleaved buffer: the stream format below asks for it.
  self->Render(static_cast<float*>(data->mBuffers[0].mData), frames);
  return noErr;
}

bool SDLCALL EventWatch(void* userdata, SDL_Event* event) {
  auto* driver = static_cast<CoreAudioDriver*>(userdata);
  if (event->type == SDL_EVENT_WILL_ENTER_BACKGROUND) {
    driver->Pause();
  } else if (event->type == SDL_EVENT_DID_ENTER_FOREGROUND) {
    driver->Resume();
  }
  return true;
}

// The session is activated on a queue of its own, started as early as
// possible (PrepareAudioSession, when the game is launched), never on the
// game's threads: setActive is a blocking call into the system's audio
// server. Some launches right after the app restarted (a settings change)
// hung for good with the game's audio thread inside it, before any game
// frame: the game waits for its audio thread, which never returned.
dispatch_semaphore_t session_ready = dispatch_semaphore_create(0);
std::atomic<bool> session_activated{false};

void ActivateSessionOnce() {
  static std::once_flag once;
  std::call_once(once, [] {
    nfsmw::boot::Trace("audio: activating the session");
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
      const auto start = std::chrono::steady_clock::now();
      AVAudioSession* session = AVAudioSession.sharedInstance;
      NSError* error = nil;
      // SoloAmbient, the iOS default for games: it respects the silent switch
      // and stops other apps' audio. Playback (the launcher switch): sound
      // with the silent switch on too; it also stops other apps' audio.
      const bool silent_mode = REXCVAR_GET(ios_audio_silent_mode);
      [session setCategory:silent_mode ? AVAudioSessionCategoryPlayback : AVAudioSessionCategorySoloAmbient
                     error:&error];
      nfsmw::boot::Trace(silent_mode ? "audio: Playback (sound in silent mode)" : "audio: SoloAmbient");
      [session setPreferredSampleRate:kSampleRate error:nil];
      // ~5 ms per callback, one game block's worth (256 / 48000).
      [session setPreferredIOBufferDuration:256.0 / kSampleRate error:nil];
      const bool active = [session setActive:YES error:&error];
      const double ms =
          std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
      nfsmw::boot::Trace(fmt::format("audio: session {} in {:.0f} ms", active ? "active" : "NOT active", ms));
      if (!active) {
        REXLOG_WARN("[coreaudio] AVAudioSession setActive failed: {}", error.localizedDescription.UTF8String);
      }
      session_activated = true;
      dispatch_semaphore_signal(session_ready);
    });
  });
}

void ConfigureSession() {
  ActivateSessionOnce();
  // Normally long done (it was started at launch). If the system's audio
  // server is stuck, the game goes on: RemoteIO starts without it, and the
  // session's settings come when it is ready.
  if (!session_activated &&
      dispatch_semaphore_wait(session_ready, dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC)) != 0) {
    REXLOG_WARN("[coreaudio] the audio session is still activating after 3 s: starting without waiting");
    nfsmw::boot::Trace("audio: session still activating after 3 s, going on without it");
    return;
  }
  AVAudioSession* session = AVAudioSession.sharedInstance;
  REXLOG_INFO("[coreaudio] session: {} Hz, IO buffer {:.1f} ms, {} output channels",
              session.sampleRate, session.IOBufferDuration * 1000.0,
              static_cast<long>(session.outputNumberOfChannels));
}

}  // namespace

void PrepareAudioSession() { ActivateSessionOnce(); }

CoreAudioDriver::CoreAudioDriver(memory::Memory* memory, rex::thread::Semaphore* semaphore)
    : AudioDriver(memory), semaphore_(semaphore), ring_(new float[kCapacity]()) {}

CoreAudioDriver::~CoreAudioDriver() { Shutdown(); }

bool CoreAudioDriver::OpenUnit() {
  AudioComponentDescription desc{};
  desc.componentType = kAudioUnitType_Output;
  desc.componentSubType = kAudioUnitSubType_RemoteIO;
  desc.componentManufacturer = kAudioUnitManufacturer_Apple;
  AudioComponent component = AudioComponentFindNext(nullptr, &desc);
  if (!component || AudioComponentInstanceNew(component, &unit_) != noErr || !unit_) {
    REXLOG_ERROR("[coreaudio] cannot create the RemoteIO unit");
    unit_ = nullptr;
    return false;
  }

  // What we hand to the unit (input scope of the output bus): 48 kHz float32
  // interleaved stereo. RemoteIO converts to whatever the hardware runs at.
  AudioStreamBasicDescription format{};
  format.mSampleRate = kSampleRate;
  format.mFormatID = kAudioFormatLinearPCM;
  format.mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked;
  format.mChannelsPerFrame = kOutputChannels;
  format.mBitsPerChannel = 32;
  format.mFramesPerPacket = 1;
  format.mBytesPerFrame = sizeof(float) * kOutputChannels;
  format.mBytesPerPacket = format.mBytesPerFrame;
  OSStatus s = AudioUnitSetProperty(unit_, kAudioUnitProperty_StreamFormat,
                                    kAudioUnitScope_Input, 0, &format, sizeof(format));
  if (s == noErr) {
    AURenderCallbackStruct callback{RenderCallback, this};
    s = AudioUnitSetProperty(unit_, kAudioUnitProperty_SetRenderCallback,
                             kAudioUnitScope_Input, 0, &callback, sizeof(callback));
  }
  if (s == noErr) {
    s = AudioUnitInitialize(unit_);
  }
  if (s == noErr) {
    s = AudioOutputUnitStart(unit_);
  }
  if (s != noErr) {
    REXLOG_ERROR("[coreaudio] RemoteIO setup failed: OSStatus {}", static_cast<int>(s));
    AudioComponentInstanceDispose(unit_);
    unit_ = nullptr;
    return false;
  }
  started_ = true;
  REXLOG_INFO("[coreaudio] RemoteIO started: 48 kHz stereo float");
  return true;
}

void CoreAudioDriver::CloseUnit() {
  if (unit_) {
    AudioOutputUnitStop(unit_);
    AudioUnitUninitialize(unit_);
    AudioComponentInstanceDispose(unit_);
    unit_ = nullptr;
  }
  started_ = false;
}

bool CoreAudioDriver::Initialize() {
  ConfigureSession();
  {
    std::lock_guard<std::mutex> lock(control_);
    if (!OpenUnit()) {
      return false;
    }
  }
  is_running_.store(true, std::memory_order_release);
  SDL_AddEventWatch(EventWatch, this);

  // Interruptions (a call, Siri, an alarm): stop at the start, restart at the
  // end. Without restarting, the game would go silent after the first call.
  id token = [NSNotificationCenter.defaultCenter
      addObserverForName:AVAudioSessionInterruptionNotification
                  object:AVAudioSession.sharedInstance
                   queue:nil
              usingBlock:^(NSNotification* note) {
                const auto type = static_cast<AVAudioSessionInterruptionType>(
                    [note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue]);
                REXLOG_INFO("[coreaudio] interruption {}",
                            type == AVAudioSessionInterruptionTypeBegan ? "began" : "ended");
                if (type == AVAudioSessionInterruptionTypeBegan) {
                  Pause();
                } else {
                  [AVAudioSession.sharedInstance setActive:YES error:nil];
                  Resume();
                }
              }];
  interruption_observer_ = (__bridge_retained void*)token;
  return true;
}

void CoreAudioDriver::Pause() {
  std::lock_guard<std::mutex> lock(control_);
  if (unit_ && started_) {
    const OSStatus s = AudioOutputUnitStop(unit_);
    started_ = false;
    REXLOG_INFO("[coreaudio] pause: {}", static_cast<int>(s));
  }
}

void CoreAudioDriver::Resume() {
  std::lock_guard<std::mutex> lock(control_);
  if (unit_ && !started_ && is_running_.load(std::memory_order_acquire)) {
    const OSStatus s = AudioOutputUnitStart(unit_);
    started_ = (s == noErr);
    REXLOG_INFO("[coreaudio] resume: {}", static_cast<int>(s));
  }
}

void CoreAudioDriver::Shutdown() {
  if (!is_running_.exchange(false, std::memory_order_acq_rel)) {
    return;
  }
  SDL_RemoveEventWatch(EventWatch, this);
  if (interruption_observer_) {
    id token = (__bridge_transfer id)interruption_observer_;
    interruption_observer_ = nullptr;
    [NSNotificationCenter.defaultCenter removeObserver:token];
  }
  // Wake whoever waits on the audio semaphore.
  if (semaphore_) {
    semaphore_->Release(16, nullptr);
  }
  std::lock_guard<std::mutex> lock(control_);
  CloseUnit();
}

void CoreAudioDriver::SubmitFrame(uint32_t samples_ptr) {
  if (!is_running_.load(std::memory_order_relaxed)) {
    return;
  }
  // The Xbox 360 audio frame lives in guest virtual memory.
  uint8_t* frame_data = nullptr;
  if (memory_) {
    frame_data = memory_->TranslateVirtual<uint8_t*>(samples_ptr);
    if (!frame_data) {
      frame_data = TranslatePhysical(samples_ptr);
    }
  }
  if (!frame_data) {
    return;
  }

  const uint64_t now_ns = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
  if (last_submit_ns_) worst_submit_gap_ns_ = std::max(worst_submit_gap_ns_, now_ns - last_submit_ns_);
  last_submit_ns_ = now_ns;
  ++submitted_;
  if (!stats_since_ns_) stats_since_ns_ = now_ns;
  if (now_ns - stats_since_ns_ >= 5'000'000'000ull) {
    const uint32_t lowest = lowest_floats_.exchange(UINT32_MAX);
    REXLOG_INFO("[coreaudio] 5 s: {} blocks, {} gaps ({} frames of silence), {} permits refused, ring at least "
                "{} blocks, longest wait between blocks {:.1f} ms | {} blocks dropped (ring full), {} trimmed "
                "(over 12 queued) | limiter: {:.2f}% of samples turned down, deepest {:.1f} dB | silent blocks from "
                "the game {} (longest run {:.0f} ms), sudden drops {}",
                submitted_, underruns_.exchange(0), silent_frames_.exchange(0), refused_permits_.exchange(0),
                lowest == UINT32_MAX ? 0u : lowest / uint32_t(kFloatsPerBlock), worst_submit_gap_ns_ / 1e6,
                dropped_full_, trimmed_, submitted_ ? 100.0 * limited_samples_ / (double(submitted_) * kSamplesPerChannel) : 0.0,
                20.0 * std::log10(std::max(deepest_gain_, 1e-6f)), silent_blocks_,
                longest_silent_run_ * 1000.0 * kSamplesPerChannel / kSampleRate, sudden_drops_);
    silent_blocks_ = 0;
    longest_silent_run_ = 0;
    sudden_drops_ = 0;
    submitted_ = 0;
    dropped_full_ = trimmed_ = 0;
    limited_samples_ = 0;
    deepest_gain_ = 1.0f;
    worst_submit_gap_ns_ = 0;
    stats_since_ns_ = now_ns;
  }

  // No room for a whole block: the NEW one is dropped. The producer never
  // touches the read index, which is what allows going without a lock.
  const size_t w = write_.load(std::memory_order_relaxed);
  const size_t r = read_.load(std::memory_order_acquire);
  if (kCapacity - (w - r) < kFloatsPerBlock) {
    ++dropped_full_;
    return;
  }
  // The latency: the game queued blocks ahead until the ring was full (64,
  // ~340 ms of sound behind the picture), and it stayed that full. Kept at
  // most kTargetBlocks deep (~64 ms); a block beyond that is not queued. In
  // steady play the game delivers one block per block played, so this only
  // trims the surplus once, when the sound starts.
  constexpr size_t kTargetBlocks = 12;
  if (w - r >= kTargetBlocks * kFloatsPerBlock) {
    ++trimmed_;
    return;
  }

  // PLANAR, 6 channels of 256 samples each (6144 bytes), big-endian.
  // Channel order: 0=FL, 1=FR, 2=C, 3=LFE, 4=BL, 5=BR.
  const uint32_t* src = reinterpret_cast<const uint32_t*>(frame_data);
  const uint32_t* ch_fl = src + 0 * kSamplesPerChannel;
  const uint32_t* ch_fr = src + 1 * kSamplesPerChannel;
  const uint32_t* ch_c = src + 2 * kSamplesPerChannel;
  const uint32_t* ch_lfe = src + 3 * kSamplesPerChannel;
  const uint32_t* ch_bl = src + 4 * kSamplesPerChannel;
  const uint32_t* ch_br = src + 5 * kSamplesPerChannel;

  // Folded straight into the ring. A block is 512 floats and the capacity is
  // a multiple of 512, so a block never wraps: one base position is enough.
  //
  // Folding 5.1 to stereo adds front, centre, LFE and surround: loud moments
  // (engine, music and effects together; several menu sounds at once) go past
  // full scale. Cut off hard (the old clamp), that is the harsh, glitched
  // sound. A limiter instead: the gain drops at once to keep the peak at
  // kCeiling, and comes back over ~100 ms. (The Android port found the same.)
  constexpr float kCeiling = 0.98f;
  const float release = 1.0f - std::exp(-1.0f / (0.1f * float(kSampleRate)));  // ~100 ms
  float* dst = ring_.get() + (w & kMask);
  for (size_t i = 0; i < kSamplesPerChannel; ++i) {
    const float c = LoadBEFloat(ch_c[i]) * kCenterGain;
    const float lfe = LoadBEFloat(ch_lfe[i]) * kLfeGain;
    const float mid = c + lfe;
    const float left = LoadBEFloat(ch_fl[i]) + mid + LoadBEFloat(ch_bl[i]) * kSurroundGain;
    const float right = LoadBEFloat(ch_fr[i]) + mid + LoadBEFloat(ch_br[i]) * kSurroundGain;
    const float peak = std::max(std::fabs(left), std::fabs(right));
    if (peak * limiter_gain_ > kCeiling) {
      limiter_gain_ = kCeiling / peak;
    } else {
      limiter_gain_ += (1.0f - limiter_gain_) * release;
    }
    if (limiter_gain_ < 0.999f) {
      ++limited_samples_;
      deepest_gain_ = std::min(deepest_gain_, limiter_gain_);
    }
    dst[i * 2 + 0] = std::clamp(left * limiter_gain_, -1.0f, 1.0f);
    dst[i * 2 + 1] = std::clamp(right * limiter_gain_, -1.0f, 1.0f);
  }

  // Diagnostics: what the game mixed. A silent block (peak under -80 dB), the
  // longest run of them, and sudden drops (a block 30 dB quieter than the
  // block before while that one was clearly audible): the whole game audio
  // cutting out in police chases.
  {
    float block_peak = 0.0f;
    for (size_t i = 0; i < kSamplesPerChannel * 2; ++i) block_peak = std::max(block_peak, std::fabs(dst[i]));
    if (block_peak < 1e-4f) {
      ++silent_blocks_;
      ++silent_run_;
      longest_silent_run_ = std::max(longest_silent_run_, silent_run_);
    } else {
      silent_run_ = 0;
    }
    if (last_block_peak_ > 0.03f && block_peak < last_block_peak_ * 0.0316f) {
      ++sudden_drops_;
      static std::atomic<int> drop_lines{60};
      if (drop_lines.fetch_sub(1) > 0) {
        REXLOG_INFO("[coreaudio] sudden drop: block peak {:.1f} dB after {:.1f} dB",
                    20.0 * std::log10(std::max(block_peak, 1e-7f)), 20.0 * std::log10(last_block_peak_));
      }
    }
    last_block_peak_ = block_peak;
  }

  // Publish the block: the release makes the consumer see the samples before
  // the new index.
  write_.store(w + kFloatsPerBlock, std::memory_order_release);
  // The semaphore is NOT released here: Render releases it as the hardware
  // consumes, which is what sets the 48 kHz pace.
}

void CoreAudioDriver::Render(float* out, uint32_t frames) {
  if (frames == 0) {
    return;
  }
  const size_t wanted = size_t(frames) * kOutputChannels;
  const size_t r = read_.load(std::memory_order_relaxed);
  const size_t w = write_.load(std::memory_order_acquire);
  const size_t n = std::min(w - r, wanted);

  // Copy what there is, in one or two pieces depending on the ring's end.
  const size_t pos = r & kMask;
  const size_t first = std::min(n, kCapacity - pos);
  std::memcpy(out, ring_.get() + pos, first * sizeof(float));
  if (n > first) {
    std::memcpy(out + first, ring_.get(), (n - first) * sizeof(float));
  }
  // Whatever is missing, silence.
  if (n < wanted) {
    std::memset(out + n, 0, (wanted - n) * sizeof(float));
    underruns_.fetch_add(1, std::memory_order_relaxed);
    silent_frames_.fetch_add(uint32_t((wanted - n) / kOutputChannels), std::memory_order_relaxed);
  }
  {
    const uint32_t level = uint32_t(w - r);
    uint32_t low = lowest_floats_.load(std::memory_order_relaxed);
    while (level < low && !lowest_floats_.compare_exchange_weak(low, level, std::memory_order_relaxed)) {
    }
  }
  read_.store(r + n, std::memory_order_release);

  // One permit per 256 frames the hardware consumes, data or not: that is
  // what clocks the game's audio thread at 48 kHz.
  if (semaphore_) {
    consumed_ += frames;
    const size_t release = consumed_ / kSamplesPerChannel;
    if (release > 0) {
      consumed_ -= release * kSamplesPerChannel;
      if (!semaphore_->Release(int32_t(release), nullptr)) {
        refused_permits_.fetch_add(uint32_t(release), std::memory_order_relaxed);
      }
    }
  }
}

// ---------------------------------------------------------------------------
//  CoreAudioSystem
// ---------------------------------------------------------------------------

CoreAudioSystem::CoreAudioSystem(runtime::FunctionDispatcher* function_dispatcher)
    : AudioSystem(function_dispatcher) {}

CoreAudioSystem::~CoreAudioSystem() = default;

X_STATUS CoreAudioSystem::CreateDriver(size_t index, rex::thread::Semaphore* semaphore,
                                       AudioDriver** out_driver) {
  auto driver = std::make_unique<CoreAudioDriver>(memory_, semaphore);
  if (!driver->Initialize()) {
    REXLOG_ERROR("[coreaudio] cannot initialize the driver for client {}", index);
    return X_STATUS_UNSUCCESSFUL;
  }
  *out_driver = driver.release();
  return X_STATUS_SUCCESS;
}

void CoreAudioSystem::DestroyDriver(AudioDriver* driver) { delete driver; }

}  // namespace rex::audio::ios
