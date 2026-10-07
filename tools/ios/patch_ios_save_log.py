#!/usr/bin/env python3
"""
Log the game's saves and the Xbox Live sign-in screen at the normal log level.

    python3 tools/ios/patch_ios_save_log.py            apply
    python3 tools/ios/patch_ios_save_log.py --status
    python3 tools/ios/patch_ios_save_log.py --revert

Touches src/kernel/xam/xam_content.cpp and src/kernel/xam/xam_user.cpp.


WHY
===

On an iPad, creating a career alias stopped saving: the game asks to sign in
to Xbox Live, and after "Do you want to save the alias NAME?" it softlocks.
None of that is in the log at info level: the XAM calls behind it log at
debug, and log_level=debug drowns everything in the audio trace. A few lines
per save are cheap, so they stay on:

  [save] create 'root' file 'name' (mode N): created|opened|..., result X
  [save] delete 'name': result X
  [save] the game asked for the Xbox Live sign-in screen
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CONTENT = "src/kernel/xam/xam_content.cpp"
USER = "src/kernel/xam/xam_user.cpp"

CREATE_ANCHOR = '''    if (disposition_ptr) {
      *disposition_ptr = static_cast<uint32_t>(disposition);
    }

    extended_error = X_HRESULT_FROM_WIN32(result);
'''
CREATE_NEW = '''    if (disposition_ptr) {
      *disposition_ptr = static_cast<uint32_t>(disposition);
    }

    // LOCAL PATCH - iOS: every save the game creates or opens, in the log
    // (tools/ios/patch_ios_save_log.py).
    REXLOG_INFO("[save] create '{}' file '{}' (mode {}): {}, result {:08X}", root_name,
                content_data.file_name(), flags & 0xF,
                disposition == kDispositionState::Create ? "created"
                : disposition == kDispositionState::Open ? "opened"
                                                         : "nothing done",
                uint32_t(result));

    extended_error = X_HRESULT_FROM_WIN32(result);
'''

DELETE_ANCHOR = '''  XCONTENT_AGGREGATE_DATA content_data = *content_data_ptr.as<XCONTENT_DATA*>();

  auto result = REX_KERNEL_STATE()->content_manager()->DeleteContent(xuid, content_data);
'''
DELETE_NEW = '''  XCONTENT_AGGREGATE_DATA content_data = *content_data_ptr.as<XCONTENT_DATA*>();

  auto result = REX_KERNEL_STATE()->content_manager()->DeleteContent(xuid, content_data);
  // LOCAL PATCH - iOS (tools/ios/patch_ios_save_log.py).
  REXLOG_INFO("[save] delete '{}': result {:08X}", content_data.file_name(), uint32_t(result));
'''

SIGNIN_ANCHOR = '''u32 XamShowSigninUI_entry(u32 unk, u32 unk_mask) {
'''
SIGNIN_NEW = '''u32 XamShowSigninUI_entry(u32 unk, u32 unk_mask) {
  // LOCAL PATCH - iOS (tools/ios/patch_ios_save_log.py).
  REXLOG_INFO("[save] the game asked for the Xbox Live sign-in screen ({:08X}, {:08X})",
              uint32_t(unk), uint32_t(unk_mask));
'''

BLOCKS = [
    (CONTENT, "log every save create/open", CREATE_ANCHOR, CREATE_NEW),
    (CONTENT, "log every save delete", DELETE_ANCHOR, DELETE_NEW),
    (USER, "log the sign-in screen", SIGNIN_ANCHOR, SIGNIN_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_save_log", BLOCKS))
