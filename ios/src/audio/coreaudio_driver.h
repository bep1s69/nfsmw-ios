// NFSMW Recompiled - audio output on iOS (CoreAudio, RemoteIO)
//
// The iOS counterpart of android/app/src/main/cpp/audio/aaudio_driver.h, with
// the same design:
//
//   - the game hands over one block at a time (256 samples x 6 channels,
//     planar, big-endian float); SubmitFrame folds it to stereo straight into
//     a lock-free ring (one producer, one consumer);
//   - the output's real-time render callback drains the ring and releases one
//     semaphore permit per 256 frames the hardware consumes, whether there was
//     data or not. That is what clocks the game's audio thread at exactly
//     48 kHz (187.5 blocks/s);
//   - the render callback never takes a lock.
//
// Output is a RemoteIO audio unit, float32 stereo at 48 kHz; if the hardware
// runs at another rate, RemoteIO converts. AVAudioSession interruptions
// (a call, Siri) stop and restart it, which is the iOS equivalent of AAudio's
// DISCONNECTED reconnect. Route changes (headphones, Bluetooth) need nothing:
// RemoteIO follows the route on its own.

#pragma once

#include <rex/audio/audio_driver.h>
#include <rex/audio/audio_system.h>
#include <rex/thread.h>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>

// The AudioUnit types, without pulling AudioToolbox into every includer.
typedef struct OpaqueAudioComponentInstance* AudioComponentInstance;

namespace rex::audio::ios {

// Starts activating the app's audio session on a queue of its own (blocking
// system call); called when the game is launched, so it is done before the
// game's audio thread needs it. Safe to call more than once.
void PrepareAudioSession();

class CoreAudioDriver final : public AudioDriver {
 public:
  CoreAudioDriver(memory::Memory* memory, rex::thread::Semaphore* semaphore);
  ~CoreAudioDriver() override;

  bool Initialize();
  void Shutdown();

  // App to the background and back (SDL events), and audio interruptions.
  void Pause();
  void Resume();

  void SubmitFrame(uint32_t samples_ptr) override;

  // The render callback (coreaudio_driver.mm). Public only so the C callback
  // can reach it.
  void Render(float* out, uint32_t frames);

 private:
  bool OpenUnit();
  void CloseUnit();

  // One game block: 256 samples per channel, already folded to stereo.
  static constexpr size_t kSamplesPerChannel = 256;
  static constexpr size_t kOutputChannels = 2;
  static constexpr size_t kFloatsPerBlock = kSamplesPerChannel * kOutputChannels;

  // Ring capacity: AudioSystem::kMaximumQueuedFrames' 64 blocks. With the
  // semaphore flow control there are never more blocks in flight than
  // permits, so it does not overflow with ANY audio_maxqframes (4-64). A power
  // of two, to index with a mask.
  static constexpr size_t kRingBlocks = 64;
  static constexpr size_t kCapacity = kRingBlocks * kFloatsPerBlock;  // 32768 floats, 128 KB
  static_assert((kCapacity & (kCapacity - 1)) == 0, "capacity must be a power of 2");
  static constexpr size_t kMask = kCapacity - 1;

  rex::thread::Semaphore* semaphore_ = nullptr;
  AudioComponentInstance unit_ = nullptr;
  std::atomic<bool> is_running_{false};
  bool started_ = false;  // under control_

  std::unique_ptr<float[]> ring_;
  alignas(64) std::atomic<size_t> write_{0};  // only the producer touches it
  alignas(64) std::atomic<size_t> read_{0};   // only the consumer touches it

  // Frames consumed by the hardware that do not yet make a whole block. Only
  // the render callback touches it.
  size_t consumed_ = 0;

  // Diagnostics, logged every 5 s by the producer (SubmitFrame): render
  // callbacks that found the ring short (each one a gap of silence: a click),
  // the frames of silence, permits the semaphore refused (it was full), the
  // lowest ring level seen, and the longest gap between two submitted blocks.
  std::atomic<uint32_t> underruns_{0}, silent_frames_{0}, refused_permits_{0};
  uint32_t dropped_full_ = 0, trimmed_ = 0;  // producer only: blocks not queued (full / over the target depth)
  std::atomic<uint32_t> lowest_floats_{UINT32_MAX};
  uint64_t last_submit_ns_ = 0, worst_submit_gap_ns_ = 0, stats_since_ns_ = 0;  // producer only
  uint32_t submitted_ = 0;                                                       // producer only
  // The output limiter (SubmitFrame, producer only): its gain, and for the log.
  float limiter_gain_ = 1.0f, deepest_gain_ = 1.0f;
  uint64_t limited_samples_ = 0;

  // The AVAudioSession interruption observer (an NSObject token, retained).
  void* interruption_observer_ = nullptr;

  // Control path only: open, close, pause, resume. The render callback never
  // takes it.
  std::mutex control_;
};

class CoreAudioSystem final : public AudioSystem {
 public:
  explicit CoreAudioSystem(runtime::FunctionDispatcher* function_dispatcher);
  ~CoreAudioSystem() override;

  static bool IsAvailable() { return true; }
  static std::unique_ptr<AudioSystem> Create(runtime::FunctionDispatcher* function_dispatcher) {
    return std::make_unique<CoreAudioSystem>(function_dispatcher);
  }

  X_STATUS CreateDriver(size_t index, rex::thread::Semaphore* semaphore,
                        AudioDriver** out_driver) override;
  void DestroyDriver(AudioDriver* driver) override;
};

}  // namespace rex::audio::ios
