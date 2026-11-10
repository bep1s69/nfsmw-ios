# Native graphics path toward an iOS port

## Current decision — November 10, 2026

Stefan approved the source-level feasibility/design pass for a renderer-work
reduction prototype, then broadened the goal: a longer project is acceptable
to remove as much Xbox 360 compatibility work as practical while preserving
current performance and visuals. This reopens the parked native-D3D work for
design. It does not approve a particular implementation or merge of the old
branch. No production behavior changes, build or device test in this pass.

Use this existing, AGENTS-indexed plan as the design home. Older version and
N0–N2a evidence remain available with `git show native-d3d:docs/NATIVE_D3D_PLAN.md`
and `git show native-d3d:docs/TECHNICAL.md`. Read the November 6 entries headed
"native D3D layer N0" through "native D3D layer parked". Do not merge that
branch wholesale: it predates the public-history cleanup and current features.
If code is reused, port only reviewed changes onto a branch from current HEAD.

## Goal and limits

Hold the selected FPS and existing frame pacing, responsiveness, rendering,
audio and gameplay with less battery consumption. Lower resolution, fewer
effects, fewer simulation updates and reduced caps are not this project's
success criteria. A cleaner architecture is useful groundwork, not evidence
of energy savings; measure both device CPU work and system energy afterward.

The executable is already ARM64 from static PPC recompilation, and the active
renderer already uses native Metal and pretranslated shaders. There is no
general CPU interpreter or Vulkan draw renderer to replace in normal native
gameplay. What remains is Xbox-shaped engine/API behavior: guest device
state, command packets, resource layouts, memory and synchronization semantics.
Those can be replaced gradually without rewriting the game's simulation.

## What the existing evidence can fund

Reprocessed dev110 iPhone 17 Pro Max pursuit, 1x/60, OS27.3, trace UUID
F21AEC52-98B9-3265-B696-195C9F82119C, running samples in trace seconds 5–120.
174,450 ms sample weight across 115s; 5.12% have no stack. Weights are a CPU
cost estimate, not exact duration or energy. TECHNICAL's independent audit
records the original paths, export and parser command.

| Measured scope | App sampled CPU | Interpretation |
|---|---:|---|
| Native render workers + GPU Commands | 46.25% | Entire cost envelope; much work must remain |
| Record inclusive | 14.84% | Includes validation, snapshots, decode, fingerprints and allocations |
| Guest D3D writer paths union CP packet work outside native callbacks | 6.675% | Upper bound on packet-bridge removal in this capture |
| Draw destructor inclusive | 2.871% | Overlaps render total; ownership simplification target |
| AGX leaf samples, all threads | 3.334% | Driver self only, not whole draw-encoding cost |

The packet-only envelope reproduces November6 N0 (6.69%) closely. Removing
PM4 alone cannot credibly promise 10% total app CPU savings. The 10% target
discussed in chat is a useful combined-project ambition, not a per-step gate
or a demonstrated result. Even eliminating all measured AGX self would be
3.33%; ICBs also require validation, updates and execution work. Do not call
the whole 46% removable or add these overlapping footprints.

## Existing native-D3D work: reuse its knowledge

Local branch `native-d3d`, tip `50885f1`, completed N0, N1 and N2a:

- Device shadow blocks and hook points were identified. N1d established that
  normal draw state also matches at the CP after resolves. A local checker
  was wrong about some resolve state; preserve that negative finding.
- N2a tested normal on iPhone: 98.2–99.0% of draws used device-object state,
  with fallbacks for inline/UP/tiling/resolve cases. This was tested coverage,
  not complete semantic equivalence of every game scene.
- N2a still wrote the entire PM4 stream, added markers and copied 2,401 dwords
  (9,604 bytes) per draw, then byte-swapped them on the CP. It was a correctness
  bridge that added work, not an optimization whose battery payoff failed.
- Replacing the stream with the same full snapshots is a bad next step:
  ~2,400 dwords per draw versus ~90 original register words per draw in that
  evidence. Normal/native state should be consumed directly or represented
  compactly. Avoid repeating N2a as a purported savings build.
- Shaders, exceptional draws, resolves, queries, fences and swap still need
  an ordered, complete design. Partial bypass must not mix two producers into
  one Frame without a sequence/ownership protocol.

## Proposed architecture

Two producers can feed one owned native frame format:

```
Existing producer: game -> PM4 -> CP adapter ----+
                                              +-> owned NativeFrame -> Metal
Future producer:   game -> native D3D adapter --+     preparation -> submission
```

The existing producer is the reference and fallback. The future producer is
the removal of the Xbox command bridge. Both use the same Metal consumer;
ICB reuse is an optional consumer optimization, not a replacement for D3D
semantics and not tied to the marker protocol.

### A. Owned frame representation and explicit completion ownership

Current `Draw` carries per-attribute shared_ptrs, index shared_ptr, two constant
bank shared_ptrs and optional prior-motion constants. A Frame dies after CPU
encoding, while pooled GPU buffers/texture lifetime and writebacks are protected
separately through GPU completion. Constant banks have a mutex/free list and a
new shared_ptr control block even when bank storage is reused. DrawArena already
amortizes attribute allocations; adding another small-list pool is not new.

Design `NativeFrame` with frame-level owners and draw handles/indices. Keep
one strong owner per distinct cached geometry/texture/version used by the
frame; draw descriptors refer to those owners. Allocate changed constant
snapshots in frame-owned stable blocks, retaining current range/copy semantics.
Do not retain pointers into cache nodes after a sweep. Keep full bank layout
initially: compacting register ranges is a separate change with CPU readers
and shader ABI implications. Motion/debug paths initially retain the current
shared ownership path or use the reference renderer.

CPU storage may recycle only after its last CPU consumer and temporal-history
reference are finished. GPU contexts recycle only after actual command-buffer
completion, including error/early-commit paths. These are distinct lifetimes.
Keep contexts bounded; when none is available, use the reference path without
adding frame latency or weakening current pacing. Bound retained high-water
memory and purge idle capacity on the existing memory-pressure signal.

This supplies a shared boundary for both producers. Storage reuse alone is
not expected to reach the combined 10% ambition; measure actual ownership/
snapshot savings rather than infer them from retained capacity.

### B. Cached Metal commands with per-frame address data

Concrete first consumer prototype: ordinary indexed, non-query, opaque game
draws with cached geometry. Leave internal blits/movies, fresh geometry,
query draws, motion passes, diagnostic dumps and unsupported cases direct.
Preserve the renderer's existing effective `draw_order`, skips, sky/stencil
policy, pass boundaries, resolve/clear positions and presentation behavior.
Do not globally reorder or deduplicate draws.

The current shaders already read a 32-byte buffer-8 structure with GPU
addresses `{vs, ps, shared, previous_vs}`. Put that structure in a stable slot
of a completion-owned context buffer instead of per-draw setVertexBytes /
setFragmentBytes. Write its current addresses every frame. Existing VS/PS
uploads can remain variable-packed: stable constant contents or offsets are
not a prerequisite if the command points to a stable address *record*.
Use conservative buffer alignment and keep the ABI unchanged.

Each context owns its ICB, push slots and descriptor heaps at stable Metal
buffer identities. Their contents reflect the current frame's textures,
samplers and constants. Grow only when that context is idle, increment its
generation and invalidate command bindings on growth. Preserve current
per-pass resolve/view heap updates and existing resource declarations.

For each current output slot, construct an exact command key: primitive,
count/type/offset, index buffer identity+generation, every active vertex
buffer binding+offset, push slot, heap buffers and relevant pipeline variant.
Compare fields (no padded memcmp or hash-only equality). Rebuild a command
on any mismatch; otherwise update the referenced data and retain the command.
Match by current slot and full key, not dev114's approximate object identity.
Hold all resources referenced by a cached command until it is reset/retired;
resident is not synonymous with owned. Never reuse a cache entry for a new
resource that merely acquired the same freed pointer/address.

Use `inheritBuffers=false`: bind heaps 0–4, address data at 8, and attributes
at 9+ inside each command. `inheritBuffers=true` would ignore those per-command
bindings. For the first portable version use inherited pipeline/raster/depth
state and execute only contiguous runs with equal effective PSO, depth/stencil,
stencil reference, bias, clipping, viewport, scissor, cull/winding and visibility
state, within the same existing render pass. Flush a run before any state or
resource dependency boundary, direct draw, resolve, clear or encoder transition.
Invalidate the ordinary EncoderState caches conservatively after ICB execution
before returning to direct draws. Start with runs of at least two commands;
count short-run fallback and net calls saved, not just eligible draws.

ICB-compatible PSOs require `supportIndirectCommandBuffers` at creation, with
cache/archive distinction from old PSOs and warmup covering the new variant.
Do not mark an existing PSO compatible after the fact. Compile failure falls
back to the normal draw, never skips visible work. Apple10/iOS26 adds ICB
raster/depth setters, but the project supports iOS18 and other GPUs: this
design does not depend on those new setters. Future hardware-specific expansion
may reduce run splits only after the portable route is useful.

Unknowns before a speed claim: compatible run lengths, same-context exact
command-key reuse, context/heap growth, validation/update overhead, added ICB
GPU time, and whether indirect execution changes useful overlap. Existing
dev114 statistics measure none of these. Initial correctness must exercise
state transitions and GPU resource lifetimes, not just a static screenshot.

### C. Direct D3D producer: remove the PM4 round trip

Reuse the known USA hooks, shader identity work and shadow layout. Replace
normal draw state emission with direct immutable native records; no full
0x6000-register image or 9.6KB marker snapshot for every draw. Snapshot CPU-
mutable vertices/indices/constants before the game can overwrite them, or use
a proved resource-version ownership scheme. A pointer to mutable device state
queued for later reading is not a snapshot.

Resolve/clear, query begin/end/answers, fences, writebacks, shader binds,
predicated tiling and swap must be represented as ordered operations. The
known normal draw hooks alone are insufficient. Initially select the producer
only at a drained frame boundary; unknown/unsupported operations must be
detected before committing a native frame, not after skipping its packets.
Drain outstanding native operations before returning to PM4 mode; preserve
guest-visible register and completion state. If safe frame fallback cannot
be established, leave the new route disabled for that content/edition.

Reuse the accepted display pacing code, cap controller and native presenter.
Remove ring-space polling only when its backpressure/completion semantics have
native equivalents. Retire the CP thread's graphics work only when no remaining
stream user requires it. Keep the runtime for unrelated kernel/game services.

Direct Record on the game thread is a candidate, not automatic spare capacity:
its inclusive CPU is ~225ms/s in today's trace, and moving it can lengthen the
critical path. Existing main-thread averages plus that work do not prove
60fps/120fps deadline safety. NativeFrame permits later compact producer +
consumer scheduling if synchronous work fails, but that design must pay for
the snapshot it needs. Reject a battery gain obtained by frame misses or added
buffering/input delay.

## Order, acceptance, and test burden

Concrete first implementation scope (proposed, not yet applied):

- `ios/src/native_renderer.mm`: native frame owners/handles, completion-owned
  command contexts, address slots, eligible-run planner, ICB/direct submission,
  PSO capability variant and sparse aggregate counters.
- Small native helper headers for exact command keys, run boundaries and
  context state transitions, with host regression fixtures in `tools/native/`.
  Actual Metal behavior still needs device validation; fake encoders cannot
  establish pixel correctness, driver cost or GPU synchronization.
- Proposed restart-only `nfsmw_native_command_reuse=false` selects the whole
  trial; reference behavior remains the default. This flag does not exist yet.
  No SDK/guest hook/shader rewrite in the first stage. Turn the existing
  repeated-draw diagnostic default off before packaging a normal test build.
- Aggregate counts every 300 frames: eligible/submitted/direct draws, run
  lengths, exact command hits/rebuilds, invalidation/fallback reasons,
  context memory/growth and preparation/submission CPU time. No per-draw logs
  or dev114-style full comparisons in energy measurements.
- Put any bounded native-input capture/replay support in this same trial
  build if needed; avoid another diagnostic-only device/build cycle. Existing
  dev114 logs are statistics, not a replayable native frame capture.

1. Implement the common frame/ownership boundary and bounded ICB consumer
   behind a default-off switch, with CP input retained. This tests the larger
   renderer-side opportunity without simultaneously rewriting guest ordering.
   Frame ownership and command reuse should have separate internal diagnostics
   so we can attribute costs even if one public trial flag selects the batch.
2. Correctness: actual helper/command-key/lifetime tests, Metal validation,
   reference-vs-prototype replay of the same captured native inputs where
   feasible, and a short on-device visual/gameplay check. Live pursuits are
   not bit-exact input pairs; compare identical captured inputs for pixels.
3. CPU gate: on-device total CPU/instruction work, critical-path and pacing
   coverage, plus command reuse/run-length/retained-memory counts. Roughly
   10% total CPU reduction is the combined ambition; if results are small,
   inspect whether the planned mechanism ran and decide whether further work
   has a concrete cost to remove. Do not launch a sequence of tiny power tests.
4. Energy gate: one same-sitting A/B pair, same cap/resolution/effects and
   brightness; system %/h with gameplay-only coverage, pacing, audio and thermal
   evidence. CPU alone is not battery acceptance. No new power matrix now.
5. Then replace the CP producer with direct D3D operations in an isolated
   branch, preserving the shared consumer. Reuse old N1/N2a findings; test
   exceptional paths and ordering rather than another normal-draw shadow lap.

This is a staged longer project. No credible schedule or total battery-saving
percentage can be inferred from the current captures. Each shipped stage must
preserve baseline quality/performance, support bounded fallback and have its
own device evidence. Do not retire the reference path merely for cleanliness.

## Later native work, ranked after graphics evidence

| Candidate | What becomes more native | Evidence / constraint |
|---|---|---|
| Resource versions and native asset caches | Decode/endian/tiling conversion once at load, native vertex/texture storage, fewer recurring guest-memory fingerprints | Current GPU Commands Fingerprint self ~20.64ms/s; full cache/format path is larger but not measured as wholly removable. Must find reliable writes/resource lifetime; never assume sampled fingerprints prove immutability. |
| Hot engine routines | Replace selected recompiled loops with equivalent native algorithms/data flow | Game/world worker ~20% app CPU, dispersed. Current executable is already ARM64; rewriting arbitrary guest functions has no automatic gain. Preserve PPC numeric behavior and game timing. |
| Audio decode/reset lifecycle | Native-owned voice/decoder lifecycle, possibly predecoded or lossless cached assets | Today's guest audio worker ~10% CPU includes game mixing and decode. Prior dev112 pool missed Init/reset. Avoid claiming the separate tiny XMA Decoder thread is the whole audio cost. Preserve loops, latency and voice behavior. |
| Kernel/job/timer adapters | Native event-driven waits and services at measured hot boundaries | Previous wake-cut trials showed no power gain; avoid a generic runtime rewrite or assuming fewer wakeups equals lower battery use. |

Assets remain private/local. Replacing formats must preserve original content;
keep source game data read-only and generated caches in ignored locations.
No need to rewrite menus, networking or save formats to begin this project.

## API/source references checked November 10

- `ios/src/native_renderer.mm`: Draw/Frame/ConstantBank and Record; PipelineDescriptor;
  RenderFrame upload/EncoderState/draw loop; GpuPool, completion callbacks and NativeSwap.
- `ios/src/native_renderer.h`, `native_draw_census.cpp`, `native_draw_arena.h`.
- Installed iPhoneOS27.2 Metal headers: MTLIndirectCommandEncoder.h,
  MTLIndirectCommandBuffer.h, MTLRenderPipeline.h, MTLRenderCommandEncoder.h.
- [Apple ICB buffer inheritance](https://developer.apple.com/documentation/metal/mtlindirectcommandbufferdescriptor/inheritbuffers),
  [pipeline inheritance](https://developer.apple.com/documentation/metal/mtlindirectcommandbufferdescriptor/inheritpipelinestate),
  [ICB pipeline support](https://developer.apple.com/documentation/metal/mtlrenderpipelinedescriptor/supportindirectcommandbuffers),
  [CPU ICB sample](https://developer.apple.com/documentation/metal/encoding-indirect-command-buffers-on-the-cpu),
  [Metal feature tables](https://developer.apple.com/metal/Metal-Feature-Set-Tables.pdf).
