// Native setup around victorgbd's Android-compatible LAN implementation.
#pragma once
#import <UIKit/UIKit.h>
#include <filesystem>
#include <functional>
namespace nfsmw::lan {
UIViewController* MakeSetup(const std::filesystem::path& docs,
                           NSMutableDictionary<NSString*, NSString*>* settings,
                           std::function<void()> launch);
}
