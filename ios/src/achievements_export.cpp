// NFSMW Recompiled - the game's achievement list, for the pre-launch screen
//
// The list lives in the game's XEX (its XDBF resource): the SDK reads it when
// the XEX loads (KernelState::LoadAchievementsData), long after the
// pre-launch screen is gone. So the game writes it out here, and the screen
// shows it from the next launch on.

#include "achievements_export.h"

#include <fstream>
#include <sstream>
#include <string>
#include <system_error>

#include <fmt/format.h>

#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/util/xdbf_utils.h>

namespace fs = std::filesystem;

namespace nfsmw::achievements {

namespace {

std::string JsonString(const std::string& s) {
  std::string out = "\"";
  for (const unsigned char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          out += fmt::format("\\u{:04x}", c);
        } else {
          out += char(c);  // UTF-8 passes through
        }
    }
  }
  return out + "\"";
}

// Writes `data` to `path` only if it differs from what is there.
bool WriteIfChanged(const fs::path& path, const std::string& data) {
  std::ifstream in(path, std::ios::binary);
  if (in) {
    std::ostringstream old;
    old << in.rdbuf();
    if (old.str() == data) {
      return false;
    }
  }
  std::ofstream out(path, std::ios::binary | std::ios::trunc);
  out << data;
  return true;
}

}  // namespace

void Export(const fs::path& documents) {
  auto* kernel = rex::system::kernel_state();
  if (!kernel) {
    return;
  }
  const auto list = kernel->loaded_achievements();
  if (list.empty()) {
    REXLOG_WARN("[achievements] the game has no achievement list to export");
    return;
  }
  const fs::path dir = documents / "achievements";
  std::error_code ec;
  fs::create_directories(dir / "icons", ec);

  const auto xdbf = kernel->title_xdbf();
  size_t icons = 0;
  std::string json = fmt::format("{{\n  \"title_id\": \"{:08X}\",\n  \"achievements\": [\n",
                                 kernel->title_id());
  for (size_t i = 0; i < list.size(); ++i) {
    const auto& a = list[i];
    std::string icon;
    if (xdbf.is_valid() && a.image_id) {
      const auto block = xdbf.GetEntry(rex::system::util::XdbfSection::kImage, a.image_id);
      if (block) {
        icon = fmt::format("icons/{}.png", a.image_id);
        WriteIfChanged(dir / icon, std::string(reinterpret_cast<const char*>(block.buffer),
                                                block.size));
        ++icons;
      }
    }
    json += fmt::format(
        "    {{\"id\": {}, \"name\": {}, \"description\": {}, \"locked_description\": {}, "
        "\"gamerscore\": {}, \"flags\": {}, \"icon\": {}}}{}\n",
        a.id, JsonString(a.label), JsonString(a.description),
        JsonString(a.unachieved_description), a.gamerscore, a.flags, JsonString(icon),
        i + 1 < list.size() ? "," : "");
  }
  json += "  ]\n}\n";
  const bool changed = WriteIfChanged(dir / "list.json", json);
  REXLOG_INFO("[achievements] {} achievements, {} icons -> {}{}", list.size(), icons,
              (dir / "list.json").string(), changed ? "" : " (unchanged)");
}

}  // namespace nfsmw::achievements
