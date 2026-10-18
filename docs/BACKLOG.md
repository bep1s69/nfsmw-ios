# Development backlog

## iPhone event-loading freeze — resolved for now; monitor

Parked at the user's request on October 18, 2026. It no longer blocks battery
optimization. No cause or code fix was established. IPA20 has since loaded
events with all optimizations disabled, Utility alone, the compiled defaults,
and defaults plus the mixed GPU buffer selector. The requested offline check
also reached gameplay, although radio state is not recorded in the log.
The previously failing all-experiments-ON configuration has not been reverified.

If it recurs, preserve the exact Extra Args, graphics settings, device/network
state and complete launch log before changing settings. Compare the guest
request-completion wait and renderer progress against the earlier failure.
Evidence and individual loading checks are in [TECHNICAL.md](TECHNICAL.md).
Do not resume the isolation sequence unless the issue returns or the user asks.

## Pipeline archive persistence

Defer to a future session as requested. A synchronous archive save previously
coincided with a roughly 2.667-second stall. Investigate persistence scheduling
and ownership separately from battery changes.

## Native GPU capture

The capture button investigation is parked. Revisit the native renderer's
capture freeze/crash separately; do not make it a prerequisite for ordinary
Power Profiler or CPU investigations.
