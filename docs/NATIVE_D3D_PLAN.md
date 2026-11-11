# Native graphics path toward an iOS port

## Current decision — November 10, 2026

**November11 dev121 same-build reference result (latest):** reference mode
verified,6600CPU-owned/ICB0,22x60FPS/no audio gaps/foreground GPU errors. Matched
102s8–110s reference->reusable: Capture-14.73%, storage-36.44%, lifecycle
union-11.51%, but wholeapp+6.17%/graphics+4.57% with~10%more nearby draw/lookup
work in reusable pursuit. Historical29%wholeapp drop also largely present
with node index, cannot credit it to flat index. Keep bounded allocation
improvement; no proven net energy gain. Stop profiling round, restore indextrue,
no power/capture request now. Next source step sectionC compact direct-D3D
producer feasibility/inventory: ordered exceptional operations, resource
snapshot lifetime, safe drained-frame fallback and old N1/N2a negatives before
hook implementation. Writer/CP union7.07%app envelope not promised saving;
no energy gate/default-on release acceptance implied. Full evidence checkpoint/
TECHNICAL. Older reference-run requests below fulfilled.


**November11 dev121 device result (latest):** reusable-index mode verified,
7800CPU-owned/0ICBframes,26x60FPS summaries/no audio gaps/foreground GPU errors.
Capture-44.08%, storage-61.46%, lifecycle union-44.28% vs dev120112s selection;
app share Capture2.50->1.97%/storage1.32->0.72% supports local optimization.
Wholeapp-28.99% and graphics-32.88% NOT attributable to this bounded change:
unchanged guest workers also27–31%lower, core placement differs; similar draw
counts do not establish exact replay or clocks. No energy proof. Keep dev121;
next one SAME-build owner_index=false reference Time Profiler+log, all other
args/settings held, nearby same route/conditions. No new IPA/power matrix until
this isolates local effect from broad run differences. Checkpoint/TECHNICAL
record evidence hashes, correctness, limitations and exact commands.


**November11 dev121 BUILT (latest):** approved reusable frame owner identity
index replaces per-frame hash nodes with contiguous lookup storage, preserves
stable deque owners/immediate Clear release, slots/hints/generations and all
validation/draw logic. nfsmw_native_owner_index=true default within opt-in
reuse; false restart-only reference. Eight host fixtures PASS. Synthetic30x4096
owner frames123330->450heap allocations,128KiBretained flat lookup capacity;
optimized host median4.960->1.999ms for this component, not device CPU/energy.
Signed IPA Desktop; next one Mac Time Profiler+log in dev120 owner-only args
with index=true, no power matrix. Retained lookup capacity logged per CPU store,
pool epoch purge releases it. Details/artifact/limits in checkpoint/TECHNICAL.


**November11 dev120 device gate (latest):** owner-only mode verified on real
device:7800CPU-owned/0ICBframes,59.8–60FPS summaries,0audio gaps/foreground
GPU errors. Same112s CPU window vs dev119 has native render queue -5.97%,
GPU Commands+15.47%, combinedgraphics+1.99%, app+3.97%. Command named paths
8133.3->69.2ms, AGXself3799.4->5143.5ms; Record+15.72% and other gameplay
workloads higher. Different live pursuits, no causal net CPU/energy conclusion.
Do not start power matrix or request another capture now. Next source target
FrameOwners' per-frame node-allocated identity map; reusable flat-index host
prototype/differential/allocation comparison preserving owner lifetimes,
ordinals/generations/validation/purge. Capture named4288.2ms/2.50%app is a
scope bound, not a predicted gain. dev120 remains available, no new IPA or
runtime-default change in this analysis session. Details in current checkpoint.


**November11 Mac-profile gate (latest):** dev119's128.8s high-rate capture shows
mechanism coverage (59.5%owner hints/62.3%GPU binding reuse) and lower Record,
driver and named cleanup work, but historical dev110 comparison has combined
graphics-thread CPU effectively flat (+0.82%); lower whole-app3.52%includes
other workload differences. Draw/frame/storage lifecycle union—not Draw alone—
falls4930.6->3310.3ms in112s. Current command-cache named paths take4.93%app
sampleweight. No causal CPU or energy benefit established. Defer power pair.

**dev120 diagnostic BUILT (November11):** independent default-true restart-only
`nfsmw_native_command_encoding` gates ICB preparation/collection/report and
context acquisition. With command_reuse=true and encoding=false CPU frame
ownership/geometry handles stay active with existing direct Metal draws.
Validation and entire draw loop unchanged. All eight ownership/encoding/geometry
control combinations and existing lifetime/preparation fixtures pass; signed
IPA delivered. Next one Mac Time Profiler pursuit+log in owner-only mode,
1x/60 and otherwise dev119 settings. No power pair until CPU/correctness supports
it; no device/energy benefit claimed. Exact artifact/commands in checkpoint.

**dev119 BUILT:** first geometry-handle implementation below is packaged.
Actual helper/reference/validation-body tests and iOS build/signature pass;
host10000repeats exercise one owner-map/one GPU selection, not device savings.
Owner hints24bytes per cache entry, per-frame binding slot16bytes, FrameRef
still32bytes. Existing field/content checks, original GPU upload/sweep and
constant history retained; nil retries. Source flag false selects reference.
Next one short phone Detailed pursuit+log, no power matrix. Artifact/full
test evidence including fixture corrections in DEVELOPMENT_PROGRESS/TECHNICAL.

**dev119 implementation scope (Stefan approved continuing):** replace the
geometry ownership handoff with frame-owned handles, keeping validation intact.
After a cached vertex/index value has passed the existing validation, capture
it directly into the frame owner table. A per-cache-entry hint records owner
table generation, stable owner address and ordinal; it skips only duplicate
ownership lookup, never guest-memory checks. Globally unique table generations
prevent stale hints on pooled storage/address reuse; changed immutable array
identity gets a separate ordinal. Fresh/rectangle arrays remain mutable only
during CPU recording and retain their existing fresh upload path. Remove the
later geometry Pin traversal in the new arm; constant/history ownership stays.

Pass the ordinal in FrameRef's existing raw-pointer storage word (raw slabs
and borrowed owners are mutually exclusive), keeping FrameRef's footprint.
On the serial render queue, two frame-local strong binding arrays indexed by
vertex/index owner ordinal resolve GpuBufferFor once per persistent value.
First lookup still updates GPU use/submission stamps and performs the exact
existing allocation/upload; failed allocation is retried rather than cached.
SweepGpu runs before these arrays exist, never mid-frame; submission number
is fixed throughout RenderFrame, including early commits. Cached buffers live
until CPU encoding ends, with normal encoder/context completion ownership
unchanged. Reference/fallback draws with no ordinal use existing lookup.

Bounded slice: this removes repeated shared-owner transfers, owner-table
lookups and GPU cache selection across passes; it does not promise removal of
Record's whole10.4% or bypass AttributeKey/fingerprint/write-watch/layout checks.
Default-ON restart-only nfsmw_native_geometry_handoff within the default-OFF
command-reuse trial; false retains dev118 ownership/lookup behavior. Validate
actual helpers under sanitizers, unchanged Record validation body, cache-value
replacement, pooled generations, reference behavior, nil retry, upload and
GPU stamps, plus existing cache/storage fixtures and iOS build before delivery.

**dev118 result (latest):** actual driving logs show97.6%fewer command resource
API calls than the reference would make for identical command-run counts.
Targeted Batch CPU sampleweight falls~33–35%; named batch-sort samples vanish.
Total app CPU essentially unchanged in driving-relative aligned windows; no
net CPU/energy benefit established by different live pursuits. Keep working
trial/default-off reuse; no more small batching experiments now. Next larger
source design: Record's geometry bundle/owner handoff (~10.4%inclusive scope,
not all removable), including downstream GPU-buffer selection and existing
validation. Avoid reintroducing failed dev112 draw-order memo. Ordered direct
D3D producer remains next major architectural stage (~7%packet bridge envelope).
No further device capture requested until concrete new source work exists.

**dev118 built (latest):** implemented incremental per-encoder command resource
declarations with flat pointer set/last-binding checks; old gather/sort path
retained via nfsmw_native_command_residency=false. Default on only within
default-off command reuse. Identical actual-code resource sets/draw operations
verified under host sanitizers, iOS package passes; device CPU/energy pending.
One~40s phone Detailed pursuit + log next, not a power matrix. Ownership,
pins/completion, shaders and producer unchanged. Current artifact/flags/test
details in DEVELOPMENT_PROGRESS/TECHNICAL.

**Phone CPU evidence (latest):** received Detailed trace, actually32s of dev116.
Its1ms time-profile samples support a fully-driving10–30s window. Record10.48%
app sampled CPU; writer/CP union7.07%; draw destructor0.44%. New command-cache
named paths4.52%, including per-batch flush/resource processing2.29%; overlaps,
not an additive or fully removable envelope. Image mappings require documented
offline inference/callsite validation because LiveContainer's manually loaded
images are absent from trace metadata. Sensitivity windows support the same
ranking; no matched savings claim. Next bounded change: incremental resource
declarations per encoder instead of repeating gather/sort for every ICB run,
preserving residency/stages/pins/completion/pass order, with differential tests.
Address this identified prototype cost before expanding the producer rewrite;
no new recording needed now. Full evidence/checkpoint in TECHNICAL/DEVELOPMENT_PROGRESS.

**dev117 checkpoint:** dev116 device log has all309known pipelines prepared and
archive save complete before game start, no later pipeline activity, watchdog
stalls or GPU errors. Guarded driving windows show66.64%ICB coverage/15.39draws
per run,29.94%key hits,59.9–60FPS summaries. No CPU/energy benefit established.
Received223-key catalog is bundled locally in dev117 for first-install seeding.
Next is one enabled Time Profiler pursuit to identify actual Record/ownership/
rebuild/encoding/destruction work before further changes or power testing.
Master mute is a separate requested feature, not an energy optimization.

**dev116 follow-up:** dev115 initially looks normal per Stefan and demonstrably
executes ICB batches, but heavy freezes accompany archive saves. Pre-game
pipeline preparation and nonblocking render-side archive reporting are now
built, awaiting device validation. This is a prerequisite to CPU/energy tests,
not another claimed battery gain. Current artifact, precise coverage and
first-install catalog limitations are in DEVELOPMENT_PROGRESS/TECHNICAL.

**Implementation update:** Stefan approved starting stage 1. The dev115
prototype is built on `codex/native-frame-command-reuse`, default-off
`nfsmw_native_command_reuse`. CPU frame-owned constant blocks/geometry owners,
bounded completion-owned ICB contexts and direct fallback are implemented.
It retains the existing CP producer, pass logic, shaders and presenter.
Host sanitizer/regression tests and iOS packaging/signing checks pass; device
correctness, CPU improvement and energy improvement are still untested.
See DEVELOPMENT_PROGRESS's dev115 checkpoint and TECHNICAL's implementation
entry for exact artifact, commands, limits and test history. The broader
producer replacement and remaining representation/optimization work below
are future stages, not completed by this prototype.

Stefan approved the source-level feasibility/design pass for a renderer-work
reduction prototype, then broadened the goal: a longer project is acceptable
to remove as much Xbox 360 compatibility work as practical while preserving
current performance and visuals. This reopens the parked native-D3D work for
design. He subsequently approved the concrete stage-1 implementation above.
No merge of the old branch is approved; no device test has happened yet.

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

Concrete first implementation scope (dev115 prototype applied):

- `ios/src/native_renderer.mm`: native frame owners/handles, completion-owned
  command contexts, address slots, eligible-run planner, ICB/direct submission,
  PSO capability variant and sparse aggregate counters.
- Small native helper headers for exact command keys, run boundaries and
  context state transitions, with host regression fixtures in `tools/native/`.
  Actual Metal behavior still needs device validation; fake encoders cannot
  establish pixel correctness, driver cost or GPU synchronization.
- Restart-only `nfsmw_native_command_reuse=false` selects the whole
  trial; reference behavior remains the default.
  No SDK/guest hook/shader rewrite in the first stage. The existing
  repeated-draw diagnostic is now default off.
- Aggregate counts every 300 frames: eligible/submitted/direct draws, run
  lengths, exact command hits/rebuilds, invalidation/fallback reasons,
  context memory/growth and preparation/submission CPU time. No per-draw logs
  or dev114-style full comparisons in energy measurements.
- Put any bounded native-input capture/replay support in this same trial
  build if needed; avoid another diagnostic-only device/build cycle. Existing
  dev114 logs are statistics, not a replayable native frame capture.

Implemented bounds/details: three CPU storage owners (up to 4,096 full constant
banks/16MiB each, with existing shared-bank overflow fallback), three GPU
contexts, 8,192 command slots/context, 256-byte address-record stride,
five heaps capped at 2MiB each and 96MiB of pinned buffers/context. Pins retain
existing buffers, not copies; this can extend their lifetime and must be
checked against memory/thermal results. The budget allows two existing32MiB
geometry chunks plus argument data. One-command runs use direct draws.
Unused slots reset and unpin each frame; pressure epochs purge idle contexts
without touching in-flight work. Slab range coverage is explicit, and a live
temporal toggle promotes escaping history to shared ownership. Motion,
repeated-draw diagnostics and CPU snapshots use the reference storage path;
early commit/GPU capture/temporal output exclude the ICB route. CPU ownership
may still run when the ICB route falls back. The original Frame draw vector
and attribute arena are not persistently recycled yet. Captured-input pixel
replay and Metal-on-device validation remain unfinished; host stand-ins only
test ownership, operands and control flow.

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
