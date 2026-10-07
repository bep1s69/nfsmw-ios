// NFSMW Recompiled - audio output on iOS (see coreaudio_driver.h)

#include "coreaudio_driver.h"

#import <AVFoundation/AVFoundation.h>
#include <AudioToolbox/AudioToolbox.h>

#include <SDL3/SDL_events.h>

#include <rex/logging.h>
#include <rex/system/xmemory.h>

#include <algorithm>
#include <cstring>

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

void ConfigureSession() {
  AVAudioSession* session = AVAudioSession.sharedInstance;
  NSError* error = nil;
  // SoloAmbient, the iOS default for games: it respects the silent switch and
  // stops other apps' audio.
  [session setCategory:AVAudioSessionCategorySoloAmbient error:&error];
  [session setPreferredSampleRate:kSampleRate error:nil];
  // ~5 ms per callback, one game block's worth (256 / 48000).
  [session setPreferredIOBufferDuration:256.0 / kSampleRate error:nil];
  if (![session setActive:YES error:&error]) {
    REXLOG_WARN("[coreaudio] AVAudioSession setActive failed: {}",
                error.localizedDescription.UTF8String);
  }
  REXLOG_INFO("[coreaudio] session: {} Hz, IO buffer {:.1f} ms, {} output channels",
              session.sampleRate, session.IOBufferDuration * 1000.0,
              static_cast<long>(session.outputNumberOfChannels));
}

}  // namespace

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

  // No room for a whole block: the NEW one is dropped. The producer never
  // touches the read index, which is what allows going without a lock. With
  // the ring sized to kMaximumQueuedFrames it should not happen.
  const size_t w = write_.load(std::memory_order_relaxed);
  const size_t r = read_.load(std::memory_order_acquire);
  if (kCapacity - (w - r) < kFloatsPerBlock) {
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
  float* dst = ring_.get() + (w & kMask);
  for (size_t i = 0; i < kSamplesPerChannel; ++i) {
    const float c = LoadBEFloat(ch_c[i]) * kCenterGain;
    const float lfe = LoadBEFloat(ch_lfe[i]) * kLfeGain;
    const float mid = c + lfe;
    const float left = LoadBEFloat(ch_fl[i]) + mid + LoadBEFloat(ch_bl[i]) * kSurroundGain;
    const float right = LoadBEFloat(ch_fr[i]) + mid + LoadBEFloat(ch_br[i]) * kSurroundGain;
    dst[i * 2 + 0] = std::clamp(left, -1.0f, 1.0f);
    dst[i * 2 + 1] = std::clamp(right, -1.0f, 1.0f);
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
  }
  read_.store(r + n, std::memory_order_release);

  // One permit per 256 frames the hardware consumes, data or not: that is
  // what clocks the game's audio thread at 48 kHz.
  if (semaphore_) {
    consumed_ += frames;
    const size_t release = consumed_ / kSamplesPerChannel;
    if (release > 0) {
      consumed_ -= release * kSamplesPerChannel;
      semaphore_->Release(int32_t(release), nullptr);
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
