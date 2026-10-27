// NFSMW Recompiled - unpacking downloaded saves for the save manager's import
// (save_import.cpp): .zip archives and Xbox 360 save packages (STFS "CON").

#pragma once

#include <filesystem>

namespace nfsmw::saves {

// Every file of a .zip (stored or deflated) under out_dir, with its folders.
bool Unzip(const std::filesystem::path& zip, const std::filesystem::path& out_dir);

// Whether the file is an Xbox 360 content package (CON, LIVE or PIRS).
bool IsStfs(const std::filesystem::path& file);

// Every file inside an Xbox 360 content package under out_dir (the emulator's
// own STFS reader).
bool ExtractStfs(const std::filesystem::path& package, const std::filesystem::path& out_dir);

}  // namespace nfsmw::saves
