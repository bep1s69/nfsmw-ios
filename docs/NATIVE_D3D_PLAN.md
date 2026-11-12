# Native graphics path toward an iOS port

**November12 cumulative review (latest user request):** scoped CPU wins exist
(dev118 Batch, dev121 reusable owner index, dev125 matching), but several optimize
new trial overhead. No proven cumulative appCPU/energy gain vs pre-pass renderer,
and no demonstrated global optimization ceiling. G2 parked. Step back to frozen
baseline/configuration assessment before more source work. ICB-only gains dormant
in latest owner-only run. Graphics settings confirmed consistently1x60/noAA/MetalFX;
workload/placement confounds remain. Exact scorecard/current action checkpoint and
TECHNICAL. No new capture/build/code/default change in this review.

**November12 bounded G2 gate FAILED — PARKED (current):** host candidate compiled
against actual complete Record vertex body/ref/OFF/ON, original captures and
validation preserved. Correctness/allocator/lifetime/failure tests pass. Complete
72case matrix fails consistent benefit: hot stable2–3%better, other stable/write/
one-active cases regress, OFF overhead. No game flag/IPA/capture. Earlier isolated
12–24%model result not acceptance. Next ONEgeometryclass authoritative creation/
update/retirement+alias source coverage, no more G2 tuning/unsafe write-watch.

**November12 G2 feasibility (latest):** actual-type host model now exists, not live
renderer code. Snapshot timing prevents assuming owner Capture can be skipped.
Capture-preserving stable6/9 stage12–24%cheaper on host, changing versions10–23%
worse: generic rollout fails cost gate. Next only bounded stable-only actualRecord
integration/reference gate, no IPA/phone request; reject if marginal. See checkpoint.

**November12 strategy clarification:** "more native" is a means, not acceptance.
ARM64/Metal and decoded-data/GPU-buffer caches already exist. G2 must beat whole
handoff cost; deeper resource-version ownership can retire repeated guest-format
work only where every relevant write is covered. Do not promise large power gains
from a small binding cache. Keep unknown/dynamic validation; assess GPU power
separately. Earlier controller configuration has observed~4.67%relative drain
improvement at60 (workload/switch confounds); recent trials no cumulative proof.
Current checkpoint fixes acceptance/one-pair limit and next source priority.

**November12 dev125 G1b device gate (latest):** normal/uninterrupted user report,
exactnewUUID/flags,6600guardedframes59.9–60FPS/0audio gaps/log errors. Named
matcher32.74%lower sample weight than firstdev124ON at nearbyGPU/placement,
wholeCPU-1.69%withdraws-2.47%: local matching win, netCPU/energy unproven.
Close matcher/capture round; next SOURCE G2 frame-owned vertex-binding bundle
feasibility/full-handoff host gate below. No more power/matcher captures now.

**November12 additional dev124 ON capture:** exact old UUID/table verified, user
normal/uninterrupted,6900guardedframes59.6–60FPS/0audio gaps/logged errors.
~56.8%attribute lookup calls skipped; named cache still90.4%Find. CPU higher
with much higherGPU time/different core placement, not causal acceptance or
dev125 evidence. Next remains first dev125 device gate; no more dev124 repeats.

**November12 dev125 G1b implemented/delivered (current):** compact exact unique used
fetch pairs, hot probe headers separate,2048descriptions now4632KiB. Full original
Record/validator/lifetime guards retained; actual dev124+compact differential and
11regressions pass. Shared-binding host matcher19–32%lower cost; full preparation
~1–7%better in repeated cases, no device CPU/energy proof. DefaultOFF/bothbatchOFF.
Next ONEdev125 correctness/TimeProfiler+log, no power matrix; checkpoint exact controls.

**November11 dev124 G1 OFF reference ANALYZED (latest):** SAME build/100us,
correct controls, common uninterrupted8–50s. ON/OFF whole CPU essentiallyflat;
lookupcall-line315.7ms lower, new named cache340.6ms, consistent with matching
cost offsetting much of benefit. No net battery/default acceptance. NO more
recordings now; next SOURCE compact/dedup contiguous binding identity and hot
key/state layout, retain all validation/lifetime controls. See G1b proposal;
no new implementation/build yet. Keep preparedOFF/bothbatchingOFF.

**November11 dev124 G1 device ANALYZED (latest):** normal gameplay accepted,
full guarded6300CPU-owned/59.8–60FPS/0audio gaps/traceGPU errors; restart/tail
segmented. ~54%actual attribute lookup calls avoided,71–74%eligible descriptor
hits. Named newcache0.643%app; Find90.07%named cost, so net gain unproven.
Next ONE SAME dev124 preparedfalse reference, onlythatflag+coldrestart, both
batchingfalse/othercontrols same/High sampling. No new code/IPA/power yet.
Current checkpoint exact controls/reason; if net result weak, compact/dedupe
Find identity is source candidate, never weaken buffer/lifetime validation.

**November11 dev124 native vertex descriptions BUILT (latest):** approved
geometry slice, defaultOFF nfsmw_native_prepared_geometry. Metadata/lazy node
handles only, reference validation/index/data/ownership retained. Host reference
and lifetime/alias/sweep checks pass, repeated-input preparation cheaper but
cold churn can lose; no phone/energy acceptance. Signed Desktop
UUIDBF5FD4C9-F7F4-3D73-8244-43777D00E9BE. Next one correctness/coverage pursuit
trace+log with preparedtrue/BOTHbatchingfalse, other owner-only controls same.
See G1 below; current checkpoint/TECHNICAL authoritative.

**November11 dev123 C1 device ANALYZED (latest):** normal gameplay accepted,
5400guardedCPU-owned frames/59.9–60FPS/0audio gaps or traceGPU/token errors.
C1 reach22.8869%reported range words vsC0~1.48%,10.61runs/batch; useful native
transport coverage, not proven CPU/battery optimization. Named transport1.37%
app; whole CPU+56% vs dev122 confounded by workload/core placement/sampling.
Keep defaultOFF/normal bothflagsfalse+coldrestart. No extra recordings/power
now. Next SOURCE proposal: reusable prepared native geometry descriptions in
Record, preserving memory validation/dynamic/UP/cache generation/lifetimes;
current exactUUIDline attribution detailed TECHNICAL. No new geometry code/IPA.

**November11 dev123 C1 BUILT (latest):** compatible state-flush aggregation
implemented after actual outer/CP source gate. Separate defaultOFF restart
`nfsmw_native_register_flushes`; current C0 control retained. Host mixed cases
faster than original but MIXED vs C0; sparse admission adds cost. No device/
energy acceptance. Signed UUID5CC1ECB2-620D-3859-8718-3FD467D59843, Desktop.
Next one pursuit Time Profile+log with batchestrue/flushestrue + cold restart,
other controls unchanged; check correctness/reach/CPU before power. See C1
contract below and DEVELOPMENT_PROGRESS current checkpoint. Older statuses
below are history.

## Current decision — November 10, 2026

**November11 dev122 device result (latest):** user reports nothing off; final
build/batchON verified.7800CPU-owned/ICB0,59.9–60FPS summaries,0audio gaps or
foreground/invalid-token errors. C0 handles6.94batches/frame,0.0698%hook calls,
1.4766%reported range words.98.91%ring-byte reduction applies ONLY to admitted
batches, not whole stream. Peak18/2048slots,0capacity fallback. Named C0 union
0.1808%app; wholeapp-10.70%/graphics-13.03% vs older102scontrol cannot be credited
to this small slice (other workers/core/GPU workload differ). No energy proof.
Keep transport as default-off foundation; close profiling round/no more capture
now. Next source C1 feasibility: aggregate compatible state updates at proved
flush boundaries, immutable ownership/publication and original foreign-operation
order preserved; outer825A3EC8CPU side effects/segment fallbacks must be proved
before wiring. Don't lower small-VMX gate or mutate published batches to boost
counts. No C1 code/newIPA yet; full direct producer C remains later. Restore
register_batches=false+cold restart for normal play while source work continues.
Details/evidence/deleted Desktop log archive in checkpoint/TECHNICAL.


**November11 dev122 C0 IMPLEMENTED/BUILT (latest):** owned dirty-register
batches wired at proved USA emitter callsites, default-off restart-only
nfsmw_native_register_batches.2048slots/unique tickets, Ready-before-ring ARM64
fence, generated guest-address mapping/skew guards; original early fallback.
SDK ordered NFRB consumer uses existing virtual range writes. Scalar>=32words,
grouped>=256; small VMX runs retained after negative host timing. Actual-emitter/
app-hook/SDK-method sanitizer differential, concurrent/ABI/alias/failure tests
and seven existing regressions pass. Signed IPA Desktop; exact final identity
BE5997C9-2607-39C4-91AC-3C2AB53739CA in checkpoint. No device CPU/energy proof.
Next one active pursuit+Time Profiler/log with previous owner-only args plus
register_batches=true. No power matrix. C0 keeps CP and every other operation;
full direct producer C remains later. No branch merge/validation/draw-loop or
shader changes. Build/SDK patch/fixture limitations in TECHNICAL.


**November11 compact-producer source audit COMPLETE (latest):** normal draw
hooks alone cannot safely retire PM4: current query writer8258E830 is outside
old8259–825Asearch range; shader/resolve/indirect/wait/writeback/swap operations
remain ordered stream users. Source-hashed offline inventory tool added,
no runtime/SDK/generated source changed. New sectionC0 below specifies first
implementation: owned dirty-register batches from known flush emitter calls,
consumed by existing CP through ordered private tokens, preserving every other
operation and Record scheduling. This replaces guest register packet building
without N2a's full-state snapshots or a new direct game-thread renderer.
Not full PM4 retirement or a claimed saving; no IPA/test recording this session.
Next implement host differential builder/ownership/publication tests before
live hooks; old native-d3d branch stays untouched. Exact sources/commands and
inventory limits in TECHNICAL/current checkpoint.


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

### C0. Audited first compact producer slice — November 11

The full direct producer in C is still the destination. Immediate whole-frame
PM4 removal is not justified by N2a normal-draw state coverage. Unknown
operations discovered after direct draws/writebacks have executed cannot be
recovered by simply rerunning the original frame: mutable inputs may have
changed and guest-visible side effects are not generally reversible.

Implemented in dev122, a smaller producer boundary: replace selected calls to the
scalar emitter825A28A8 and grouped-constant emitter825A2A60 with owned native
register-delta batches. Keep original shader loads, draw packets, indirect
buffers, resolves, query events, waits, writebacks and swap in the SAME stream.
The CP remains the only Frame/Record producer, and consumes each native batch
at its token position before handling the next packet. This is a partial
packet-building bypass, not a retired CP thread or general native D3D renderer.
October22 P1a fast-runs already batches CP dispatch; C0 must remove guest
emitter/header/filler work too, not claim that old optimization again.

#### Audited operation ledger

| Operation | Source boundary found | Constraint for C0 and later retirement |
|---|---|---|
| Dirty register state | 825A3EC8 calls825A28A8 eight times,825A2A60 twice,825A2968 once,825A2B88/825A38F8; device masks+16/+24/+32/+40/+48 | Intercept only proved emitter callsites/parameters first; other helpers remain original. Scalar bit=1word, grouped bit=16words (four float4), MSB first. Keep writes in original order. |
| Draw/index/UP/inline | 82593818/82593A58 plus825930E0/82593408/8259A308; additional static candidates | Original writers and CP draw callbacks remain. UP reserves memory filled AFTER return; do not snapshot its data at entry. Predicated tiling uses alternate command storage. |
| Shaders | 825A38F8; IM_LOAD/IM_LOAD_IMMEDIATE in CP | Device register blocks omit active shader objects. Preserve loads, microcode validation/hash/memo and shader lifetime, not merely program-control registers. |
| Resolve/clear | 82592340 and825A40E8 restore helper; NativeResolve captures rectangle from fetch0 | Quad state, bin predicates, rectangle bytes and restoration are ordered operations. Do not substitute game shadow for resolve state. Static possible8259A308 call does not override N1c's zero observed nested calls. |
| Query | 8258E830 emitsEVENT_WRITE_ZPD(5B); native backend override/CpOcclusion | Outside old8259search range. Preserve begin/end sentinel/address-minus0x20 handling, delayed Metal count and exact guest result ABI. Not just VIZ_QUERY(23). |
| Predicates/indirect | SET_BIN_MASK/SELECT,82596A20 indirect-buffer candidate | Eligibility evaluated in CP against bin state/one-pass adjustments. Do not pre-evaluate on game thread or assume hooked ring is entire stream. |
| Wait/fence/writeback | e.g.825A52B0(REG_TO_MEM/SHD),825A20A8/825A2188(COND_WRITE), many WAIT_REG_MEM candidates | Preserve masked comparisons, endian addresses, register side effects, counter/event values and current completion semantics. Existing SHD stores can occur on CP rather than waiting for Metal; don't invent new early/late fence semantics. |
| Swap/pacing | 825987E0 -> kernel VdSwap builds fetch+XE_SWAP; CP swap | Keep IosCapBeforeSwap,NativeSwap,IssueSwap,NfsmwAvisarSwap,counter order. Device swap hook alone does not own all presentation state. |
| Register side effects | CP WriteRegister, native backend WriteRegistersFromMem | Scratch writes, coherency/gamma, MSAA/one-pass transforms must remain. Use virtual range-write route; raw register-file memcpy is invalid outside eligible constant banks. |

The ACTIVE plugin is NativeCommandProcessor in SDK src/graphics/plugin_main.cpp
(log confirms native backend/no Vulkan), not VulkanCommandProcessor. Its
WriteRegistersFromMem override already bulk-copies eligible constant banks;
all other registers go through base WriteRegister. The Vulkan override is a
secondary compatibility case; do not add Vulkan bookkeeping to native mode.
Current prepared SDK retains old NFD3 NOP support, but current app emits none;
that does not mean N2a is active. Prepared SDK is a source copy, not a Git repo;
hash exact inputs rather than infer a branch revision.

#### Owned delta and publication contract

- Scope first to USA/known ordinary825A3EC8 emitter callsites and validated
  base/mask/source bounds; unknown callers/modes/segment situations call the
  ORIGINAL emitter before anything has been skipped. Do not override every
  function with a matching literal or rely on N2a's~98%normal-draw coverage.
- Build ordered `{register,count,payload_offset}` spans and own copies of ONLY
  dirty big-endian values at the emitter call. No queued device-shadow pointer,
  no full0x6000register image, no mandatory2401dword snapshot per draw. Two
  source annotations define masks: scalar one bit -> one word; grouped bit ->
  sixteen words. Handle zero/all64bits without undefined shifts. A64-bit mask
  gives at most32separate runs; grouped full mask1024payload words. Capacity
  and descriptor bounds must be checked before using the batch path.
- Reserve bounded host storage AND a valid ring-token location first. Publish
  immutable batch Ready with release semantics BEFORE making its token
  visible. Consumer validates generation and acquires, calls virtual
  WriteRegistersFromMem for spans in order, then releases slot/storage. Never
  recycle via id%4096 over an in-flight record. N2a's post-draw publication
  produced not-ready fallbacks; C0 cannot ignore such a token because original
  register packets have been omitted.
- Failure before token publication leaves original writer's inputs/memory
  unchanged and runs it once. After publication there is no silent 'skip token
  and fallback': the immutable record must remain available until consumed.
  No mid-frame producer switching/replay or assumed rollback of guest writes.
  Backpressure/pool exhaustion must fall back before commitment, never wait
  while holding a lock the CP needs to release slots.
- Ring boundaries are NOT interchangeable: emitters compare against device+4,
  normal draws check+8; +0is the last word written. Scalar slow helper825A27F0
  can split a run and call82597070. Grouped emitter aligns VMX payload using
  type2 fillers. Initially keep boundary/unsupported cases original until a
  reservation adapter proves segment behavior. Old N2a's+8/64byte marker check
  is not sufficient proof. Preserve later UP pointers and required alignment.
- Small writes may be cheaper as original packets than a multiword token plus
  pool work. Determine threshold by host tests/measurements; don't replace
  one cheap register write with a larger transport by default.
- CP order preserves all existing resource reads/snapshots: vertices, indices,
  textures and resolve rectangles still read by existing Record/Resolve at
  their packet positions. No cross-thread NativeDraw call or new game-thread
  Record work, no altered guest fence/query completion, no shader changes.
- Restart-only default-off `nfsmw_native_register_batches` added in dev122;
  other dev121 settings unchanged. SDK patch apply/revert/status and shared
  library rebuild are implemented and checked. Scalar>=32/grouped>=256dirty
  words admitted; smaller batches stay original based on host crossover tests.
  Device correctness/CPU/energy acceptance remains pending.

#### First implementation and acceptance

1. Native dirty-run builder/owned bounded pool and token state machine, host
   differential against actual generated scalar/grouped emitter output and
   existing virtual CP range side effects. Include masks, endian values,
   snapshots modified after capture, source bounds, full/empty capacity,
   stale tickets, release-before-publication, concurrent completion, segment
   limits/alignment, unsupported modes and untouched fallback memory. Test
   exhaustion/failure before commit; no silent missing-state recovery.
2. Only after this evidence, wire guest emitter hooks + CP private-token patch,
   caller whitelist/early fallback, immutable ownership and sparse counts.
   Keep reference route and offline comparison in SAME build. No N2a wholesale
   branch merge, no resetting caches/shader libraries or new Metal draw path.
3. Build/sign and one focused device correctness/CPU check with existing
   consumer/geometry/ICBs held fixed; inspect token consumption, fallback,
   bytes copied, unchanged state/ordering, memory and pacing. No fresh trace
   request until concrete live build is ready; no power matrix or projected
   saving from7%writer/CP envelope. Later full C must still solve the entire
   operation ledger before retiring PM4/CP synchronization.

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


### C1. Compatible updates in one state flush — November 11

Outer825A3EC8 runs vertex825A2B88 and shader825A38F8 BEFORE its first register
emitter. Its audited suffix has8scalar825A28A8calls,2group16 ALU825A2A60calls,
and1fetch825A2968call, with CPU dirty-mask/sentinel writes between them and no
other helper/submit/wait/query/draw. Generated-source inventory is asserted in
`tools/native/test_register_flushes.py`; don't add a foreign observer inside
this suffix without a before-call barrier. This relies on the existing device/
ring producer ownership contract; it introduces no new cross-thread device
access, lock or reader synchronization. Host fixtures cannot prove all game
thread behavior or hardware-visible effects. Publication before the outer
returns ensures following draw/submit/query users see complete state.

The new outer hook executes the ORIGINAL generated function in a thread-local
collector scope, never substitutes shader/vertex bodies or CPU mask clears.
Estimate>=128dirty words and>=2bank groups admits a candidate; estimate is only
a cost gate, exact masks/roles/source bounds are rechecked at every emitter.
Prefix helpers may change dirty state, so snapshots happen at each actual
emitter, after those helpers. Each append copies only dirty BE words into a
Writing slot. No sorting: source order descends4900->2000 and can repeat a
register; CP virtual range calls preserve the original run sequence.

Fetch mask bits represent6words and only32slots, source=device+1152, base4800,
return825A3FD0. Its original packet header uses8-byte alignment, distinct from
ALU VMX16-byte alignment. Virtual original-end follows exact original footprint
through collected emitters. Token must fit and preserve final mod16. Original
source skew/size, device/ring nonalias and segment-fast-path checks precede
skipping each emitter. Device+0 remains at the collected prefix's start until
its token is written; ring must not alias ANY known device state/source.

1024words/32runs per existing slot; if append cannot fit, publish collected
PREFIX at its original position, then retry current call once from compressed
actual pointer. Unknown/slow calls commit prefix BEFORE original current call
and suspend collection throughout its helpers. Nested outer scopes commit
parent first; RAII restores TLS even when an inner original throws. Normal
exception unwinding also publishes the owned prefix, no replay. Ready data is
immutable; same unique-ticket/2048slot pool and SDK consumer reused unchanged.
Unexpected ring pointer/limit modification while a prefix is pending aborts:
this is not a safe after-the-fact fallback opportunity. Unsupported paths must
be recognized before their effects. Does not retire CP, packet submission,
Record, query/shader handling or any GPU lifetime mechanism.

Two independent defaultOFF restart flags: batches=C0individual-call route,
flushes=C1outer route. An active C1 collector supersedes C0 for its calls;
sparse flushes may use C0 if enabled. Device trial uses bothtrue, dev122-style
reference can keep batchestrue/flushesfalse; bothfalse is normal play. Activity
reports include eligible outer flushes, collected emitter calls, sparse bypass,
combined batch words/runs/bytes and pending. C1 boundary/capacity counters count
failed preparation attempts (up to2per current call), not discarded commands.
Single-run C0 counter interpretation must not be copied blindly to C1.

Host actual outer + actual three emitters/app hooks/CP ranges compare1200
mask/alignment cases permode, finalregisters/runorder/baseWriteRegister call
order/all11996device bytes except compressed pointer/nonvolatile ABI. Test
private snapshots, bank/run capacity/no partial append, unknown/segment/pool
fallbacks, nested scope/exception TLS, native-backend/consumer gates, aliases,
and high-physical source/ring mapping. Shader/vertex and segment helper bodies
are stand-ins; base WriteRegister records effects rather than executing the
hardware-side transforms. Not a GPU/game validation. Host mixed-state cases
16ALU words through1024words/bank can reduce packet work, but final measured
cost vsC0 is mixed and sparse path costs~8ns/flush. Do not infer whole-game CPU
or energy savings. Next device coverage/correctness/profile gate in checkpoint;
no power request until useful measured work reduction.

#### C1 device gate and next geometry source proposal

Dev123 capture passes this pursuit's functional/coverage gate, with Stefan's
normal picture/controls/audio confirmation. Not net CPU/energy acceptance.
18full guarded windows5400frames;360862079words/1894405batches,22.8869%range
words (approx independently phased reports),10.61runs/batch,peak1792/2048slots.
Capacity report mixes append split and slot reserve failures, so cannot infer
pool exhaustion/lost state. Prefix fallback remains necessary. Do not grow
pool or lower sparse gates without evidence. Named helpers/consumer cost1.37%
app is useful snapshot/copy work too, not exact added overhead. Broader CPU
comparison is confounded; current checkpoint/TECHNICAL retain exact numbers.
Both flags remain off for normal play, existing C0/C1 controls kept for later.

Read-only source follow-up identifies Record as14.59%app inclusive, with
9970ms self in82s. Verified UUID+atos/bounded disassembly maps1345ms to
AttributeEntryFor caller3138,514ms to end-of-attribute local release3334,
742ms to draw append3587. These call-line/skid weights are not exact functions'
removable costs. Proposed next source boundary: cache a complete prepared
native geometry description (shader-derived fetch layout/remaps, index-range
identity and validated attribute-entry handles), above per-attribute lookups,
so repeated draws can reuse setup across passes/frames. Existing mutable source
fingerprint/watch/dynamic checks MUST still execute as required. UP data,
changed shader/fetch/index formats/ranges, cache sweep/erasure/purge, allocation
identity and frame/GPU lifetime differences invalidate or fall back BEFORE
publishing a draw. Generation-checked cache node handles must not survive
entry erasure. Do not cache a completed mutable Draw/state packet blindly or
reuse geometry merely because its address matches. No new implementation yet;
source feasibility and actual reference/differential before live hooks/build.
GPU13.367ms nearby vs7.564control remains a workload confound; sparse main-pass
labels don't identify a safe equivalent shader rewrite. No parked GPU capture
or unrelated defect reopened in this analysis.

### G1. Prepared native vertex descriptions — November 11

First implementation of the approved geometry proposal is deliberately scoped
to vertex preparation, not cached whole Draws or index buffers. It reuses the
existing CachedFetchLayout/full microcode identity and retains the exact
per-draw index validation before selecting an actual lo/count. A new bounded
2way/1024set table owns metadata and borrows attribute-cache NODE addresses,
not their mutable decoded values.5016KiB process bound, allocated only on first
eligible draw, independent defaultOFF restart flag nfsmw_native_prepared_geometry.
No decoded array, Metal object, frame ref or validation result stored in it.

Exact descriptor key: normalized shader key, FULL microcode hash, dword count,
physical mapping base, actual vertex lo/count, input count and first binding
anchor. Hash is selector only. Every participating fetch pair is checked on
hit (not all texture/fetch registers); metadata in ShaderStore immutable after
Load. Physical() is SDK physical_membase+(guest&0x1fffffff), so Physical(0)
identifies mapping replacement. No layout/vector pointer retained through
fetch-layout cache clearing. All input formats, signed/integer conversion and
swizzle/mini-fetch resolution still come from original layout/decoding code.
Same index contents/format producing same vertex range may reuse vertex-only
metadata safely: index data and primitive conversion are not cached here.

Metadata includes source/range/remap/motion term and lazy CacheEntry handle.
Node handle is acquired at ORIGINAL Record lookup site, never eagerly for a
later input the original might not reach after failure. On every draw the
original watched/fingerprint/dynamic/content checks run, then original decoded
version publication/FrameOwners capture. Cached node value can change without
retargeting already-recorded frames; the table doesn't pin decoded versions.
Record's existing swizzle diagnostics still execute at their original cadence.

A cold identity occupies a probation way and takes reference preparation; only
its repeated observation fills metadata. Both ways carry probation separately
so colliding meshes can both promote. Low-input shaders(<4) and>16inputs,
legacy/no hash/no layout, invalid/out-of-range fetch, UP/inline/fromarguments
and rectangle paths take reference. No new fallback after validation effects.
Cache miss can still cost extra; no universal speedup claim. Counters are plain
CP-thread per-Frame fields, published through existing Frame handoff; render
thread logs configured table bound, never races on CP table allocation.

SweepAttributeCache invalidates generation BEFORE any Sweep erasure/purge;
old entry addresses never matched after invalidation. Conservative invalidation
every256frames also avoids unknown erasure assumptions. Unsigned generation
wrap clears slot generations before restarting. No GPU consumer ever reads a
description pointer. No frame/GPU completion or source-validation rule changed.

Actual helper plus BOTH Record preparation sites (current vs1bbb88b) compile
in host fixture,90k comparisons per enabled/disabled mode, positive saved-lookup
assertions, node replacement/dynamic/alias/map-change/lifetime/sweep/generation/
collision/probation checks. Static whole-Record normalization permits only the
explicit metadata/lookup changes: all remaining content/index/decoder/state/
ownership code must equal reference. This doesn't execute GPU/draw rendering;
shader layout and memory mapping are stand-ins, validation preserved by source
guard rather than full game execution. Host benchmark preparation-only has
positive repeated4–9input cases and negative cold churn cases. Next device gate
in checkpoint; no predicted14.6%Record or battery saving.

#### G1 device coverage gate — November 11

Dev124 passes this pursuit's functional gate with user normal-gameplay report.
Known bust/restart pause at62.623/resume65.659s isolated in55–74s; primary
8–55s and post74–100s, tail separate. GPU rises~85s, CPUlatepeak111s; don't
infer NPC-specific cause from a total timing. Cold initial/off-background
windows excluded from acceptance. All clean selected3600frames60FPS,0audio gaps.

Pre same-run avoided15,547,949of28,806,489equivalent attribute lookup sites
(53.9738%); real original calls13,258,540. Post54.2756%, full guarded54.9464%.
Equivalent sites are measured calls+saved-site counters, not an executed OFF
run or CPU saving. Pre eligiblehits71.45%/all geometrydrawhits44.50%; bypassed
small/exceptional draws matter. No table size/validation changes proposed.

Prepared named union381.8ms/47s,Find343.9ms (90.07%). Names exclude some
inlined setup and include useful preparation/miss handling, not exact overhead.
Whole-app comparison with dev122 is confounded (different C0 flag/pursuit/
placement, unrelated workers also slower). Therefore next single same-build
OFF reference is now justified by high reach+measurable matching cost. Keep
both batchingOFF and change only prepared flag false+coldrestart; no new build
before matching source-line/profile attribution. Use stable intervals and
normalize workload as needed; don't repeat uncontrolled captures indefinitely.
If net benefit is weak/negative, source candidate is a compact contiguous key
of unique used fetch pairs before full descriptions. Current matcher revisits
strided per-input metadata, often repeating an interleaved binding. This is
an inference/next optimization candidate, NOT a new implementation or measured
saving. Preserve all exact identity checks and original mutable validation.

### G1b. Compact prepared-geometry matching — next source boundary

Same-build OFF reference now supplied/verified. Common42s pre-interruption
window ON/OFF app52883.8/52909.9ms, Record7041.3/7031.7ms, ONdraws+3.36%,
nearby GPUequal. ~54.7%lookup calls removed but no clear net CPU/battery win.
Same binary's sourcecall-line3246 drops716.9->401.2ms while named cache uses
340.6ms,90%Find. Source-line/skid/inlining bounds mean no exact overhead math,
but the matching stage is the concrete next cost lead. Close recording round;
no more uncontrolled captures or power pair before source improvement.

Proposed change within existing defaultOFF trial: a compact contiguous key of
unique USED fetch pairs plus existing shader/fullhash/dword/map/range identity,
with hot state/key stored separately from large descriptions. Today Find walks
strided per-input descriptions and often repeats the same interleaved binding;
slot generation/key placement can also pull cold payload cache lines. Compare
each unique selected pair's TWO words exactly once; dedup only repeated indices,
never ignore distinct inputs or rely on selector hash as identity. Retire
redundant per-input key storage so cache bound doesn't grow. Metadata belongs
to current immutable shader/layout identity; no mutable register pointer kept
for deferred reading. Legacy/invalid/UP/dynamic content rules unchanged.

Retain same bounded capacity, admission/probation behavior, before-erase
invalidation, generation wrap/physical alias semantics and lazy node acquisition.
No cached validation result, decoded-array version or GPU/frame lifetime change.
Test all used binding mutations (including non-first slots), repeated slots,
unused-word mutations, selector collisions, replaced layouts/fullhash and all
existing reference/lifetime/sweep cases. Same complete Record/validator guard
must hold. Benchmark actual matching/preparation vs current G1 and original,
including hits, cold, churn and small bypass; no logical-call saving treated
as device CPU/energy result. November12 implementation now delivered as dev125;
see current checkpoint and TECHNICAL for exact tests, costs, artifact and next gate.


### G2. Frame-owned completed vertex bindings — next source feasibility boundary

Dev125's compact matcher reduced local cost but now accounts for only0.441%of
app CPU in8–50s; eliminating that remaining named cost affects only a small
fraction of app CPU. Inlined matching work may sit outside that named scope. Recordself4.169s/8.02%app is much
larger. Verified dev125 PC map points to2.218s of self samples in attribute
preparation/validation/decoding/collection, plus separate0.666s named owner
Capture,0.302s draw-append call line. These overlap in inclusive views, include
required useful work, and are NOT a removable-cost sum. Some221ms map to inline
headers and446.8ms to line0; don't invent exact source attribution for them.

Evaluate reuse of a COMPLETED immutable frame-owned attribute/binding bundle
for repeated passes over unchanged validated geometry. Today G1 reuses metadata
and cache-node addresses, but Record still acquires current decoded versions,
constructs/pushes every Attribute and captures ownership per input per draw.
A frame may retain one completed list and let several Draws refer to it ONLY
when their shader input layout and current decoded versions/locations/integer
semantics match exactly. Bundle lifetime belongs to Frame storage, independent
of mutable G1 cache eviction, sweep/purge and next-frame preparation. Do not
point GPU work into table slots or vectors that may be replaced.

All current index/range/content fingerprint/watch/dynamic/UP validation must
still execute in original order. Validation is not the cacheable result. Changed
source/version must publish a new bundle; failure cannot eagerly acquire later
inputs or reuse partially assembled state. Same pointer/address alone is never
proof. Per-draw fresh/upload decisions differ on first use and must be stored
separately from immutable attributes or take original fallback. Rectangle
expansion mutates copied attributes: keep it reference. Exceptional paths,
allocation failure, empty/minimal inputs, cross-frame version changes, physical
aliases, in-flight GPU completion and memory-pressure purge all need explicit
reference/lifetime checks. No full-Draw/state/texture/constant caching implied.

First inspect feasibility against actual original preparation/ownership/output
semantics; prototype behind existing host extraction with a narrowly explicit
normalization for the proposed handoff changes, retaining validators unchanged.
Measure COMPLETE handoff against current dev125, not just bundle lookup/call
counts; include same-frame repeated passes, changed decoded versions, cold/churn,
small input bypass and failure paths. Added version matching can consume savings
again: reject/park if full host benefit isn't meaningful. No new IPA/device/power
request until that gate supports it. This is a proposed source boundary, no G2
implementation, flag or default promotion yet. Current checkpoint is authoritative.


#### G2 host feasibility result and mandatory snapshot constraint — November 12

Host-only test tools/native/test_geometry_bundle_feasibility.py extracts real
renderer types; models original list+owner handoff, optimistic bundle, and a
conservative bundle retaining all original per-input Capture calls. No Record/
validation/GPU execution. Mesh IDs and post-validation owner versions are supplied;
production selector/capacity/admission/failure handling not implemented. This is
feasibility, not production/full-Record correctness or a battery benchmark.

Source boundary: a later input can see a replaced cache entry/decoded version.
Collecting raw pointers to CacheEntry.value for later capture could retarget or
release earlier input versions, and changes partial-failure effects. Thus no
safe general proof for capturing owners only on bundle miss. Preserve exact
original capture sites/timing and collect frame-owned version handles instead.
The optimistic arm is an explicit negative design control, NOT shipping evidence.

Conservative stable6/9input32/512mesh handoff+lookup+teardown12–24%cheaper host;
changing versions4/6/9 at those sizes10–23%worse. Sixteen-input stress benefits
do not represent normal known shader widths. General rollout rejected, no IPA.
Bounded stable-only eligibility/fallback might be viable, but must be tested
with actual Record failure/validation/capture ordering and candidate collection/
matching/consumer costs; host model's given-key/free validated-input assumptions
must not slip into a claimed implementation win. All original mutable validation
and unsupported paths remain required. Version matching never justifies trusting
unchanged guest address or enabling historically unsafe write-watch blindly.


#### Bounded G2 actual-preparation gate — failed and parked, November 12

Implemented host-only tools/native/stable_bindings_candidate.h and
 test_stable_binding_record.py. Actual entire Record vertex body, fetch parse/
layout cache/decoder/fingerprints/memo/MotionMix and owner captures are compiled
against reference/OFF/ON. Inverse source-edit guard allows only reserve/list
collection/publication changes.6–16known decoded non-dynamic inputs, per-frame
512bundles/512hints/8probe bounds. Opaque prepared-slot pointer only selects a
candidate: current per-input captured versions/location/integer/nonfresh state
must match exactly. Mismatch restores earlier matched prefix and blocks cohort
for remainder of frame; unknown/dynamic/fresh cases reference. Stale hints checked
by frame epoch before borrowed state; immutable outputs never refer into G1.
Allocate deque slot before equal-allocator list swap; bad_alloc retains original
list. Indexed consumer preserves LAST duplicate location/unknown-index fallback.

3000historicaldraws/arm/memoON+OFF pass ASan/UBSan, actual integer/remap/memory/range/
layout updates and exact original owner order/stats. Actual late decode bounds
failure after matched prefix publishes nothing; capacity, epoch, allocation and
version/fresh/dynamic prefix tests pass.72cost cases (7trials/20000draws/realistic
3000draw frame resets) include all selector/init/fallback/consumer/teardown costs.
Current memoON stable6/9 full-active32meshes only2–3%better;512mesh stable and
one-active/write cases often worse; OFF overhead too. Unindexed list reuse alone
loses, indexed consumption does not restore a consistent win. No whole CPU/power
acceptance, no new IPA/capture. G2 PARKED, do not continue micro-tuning this cache.

Candidate header remains outside ios/src glob and has no game includer. Synthetic
little-endian float32 layouts, index ranges supplied, other index/texture/state/
Metal/GPU bodies not executed. Source game unchanged. Keep reproducible negative
result, not another phone trial. Next larger boundary: prove ONEgeometryclass
create/update/retire/alias coverage before native resource lifetime/version work.
Keep unknown/dynamic data on reference; no immutability guesses from age/address.


#### Consolidated dev125 power comparison — November 12

Same-sitting flag-group A/B now has a positive observed energy signal: estimated
system drain40.0569->37.1388percentage points/hour (-7.28%relative), alternate
preselected trims -6.70/-6.87%. Both60FPS medians, no audio gaps, user normal.
A ownership/preparedOFF versus B ownership/preparedON; ICB/register transportOFF
both. Keep B working on this phone; no default promotion/new IPA/extra capture.
This does not establish pristine pre-pass gain, CPU-time reduction, or universal
percentage. Instructions essentiallyequal; CPU-associated impactlower/GPUimpact
higher. Pursuit/order/warm-up confounds retained in TECHNICAL. G2 stays parked;
new architecture must remove measured recurring work with validation preserved.
