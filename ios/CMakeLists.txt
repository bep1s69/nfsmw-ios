# =============================================================================
#  NFSMW Recompiled - iOS app (arm64, iOS 26+)
#
#  Configure with the preset in ios/CMakePresets.json, not by hand:
#      cmake --preset ios
#      cmake --build --preset ios                 the app
#      cmake --build --preset ios --target ipa    ios/build/NFSMW.ipa, for LiveContainer
#
#  The build folder is ~/Library/Caches/nfsmw-ios/build, OUTSIDE the
#  repository: when ~/Documents is in iCloud Drive, the file provider tags
#  everything with extended attributes (com.apple.fileprovider.fpfs#P), puts
#  them back if removed, and codesign refuses to sign a bundle carrying them
#  ("resource fork, Finder information, or similar detritus not allowed").
#
#  Like Android (android/app/src/main/cpp/CMakeLists.txt), it builds:
#
#    librexruntime.dylib     the patched SDK (tools/ios/prepare_sdk.py)
#    librexgpu-xenos.dylib   the GPU plugin, which the SDK loads with dlopen
#    NFSMW                   the app executable
#
#  and packages them into NFSMW.app with MoltenVK.framework:
#
#    NFSMW.app/
#      NFSMW, Info.plist
#      Frameworks/librexruntime.dylib
#      Frameworks/librexgpu-xenos.dylib
#      Frameworks/MoltenVK.framework
#
#  All in Frameworks/ because that is where the SDK looks on iOS
#  (tools/ios/patch_ios_paths.py) and what LiveContainer signs.
#
#  TWO MODES, depending on whether there is generated code:
#
#    with the game   ios/generated/default/sources.cmake exists (your own
#                    default.xex and tools/ios/generate_code.py). The app runs
#                    the game when it finds an ISO in Documents/, and the probe
#                    otherwise.
#    probe only      no generated code: the app only carries the Vulkan probe.
#
#  THE APP WITH THE GAME CARRIES THE GAME'S TRANSLATED CODE. Like nfsmw.exe and
#  the APK: for your own devices, NOT to be shared.
# =============================================================================

cmake_minimum_required(VERSION 3.25)
project(nfsmw_ios LANGUAGES C CXX OBJC OBJCXX ASM)

if(NOT IOS)
    message(FATAL_ERROR "This is for iOS: configure with  cmake --preset ios  (see ios/README.md)")
endif()

set(NFSMW_REPO "${CMAKE_CURRENT_SOURCE_DIR}/.." CACHE PATH "NFSMW Recompiled repository root")
set(NFSMW_SDK "${NFSMW_REPO}/../rexglue-sdk-ios" CACHE PATH
    "ReXGlue SDK prepared for iOS (tools/ios/prepare_sdk.py)")
set(NFSMW_BUNDLE_ID "com.bep1s.nfsmwios" CACHE STRING "App bundle identifier")
set(NFSMW_GEN_DIR "${CMAKE_CURRENT_SOURCE_DIR}/generated/default" CACHE PATH
    "Generated code for iOS (tools/ios/generate_code.py)")
# How many GENERATED files compile at once. Each is a huge block of C++ and
# clang can take more than 2 GB for one: with 16 GB of RAM and eight at once
# the Mac runs out of memory (the same limit as Android). The rest of the SDK
# has no limit.
set(NFSMW_JOBS_RECOMP "4" CACHE STRING "Generated files compiled at once")
get_filename_component(NFSMW_REPO "${NFSMW_REPO}" ABSOLUTE)
get_filename_component(NFSMW_SDK "${NFSMW_SDK}" ABSOLUTE)

# The SDK must be prepared for iOS, not just cloned: without REX_PLATFORM_IOS
# the libraries would be looked for next to LiveContainer's executable.
set(_mvk_marker "${NFSMW_SDK}/.nfsmw-ios/MoltenVK/v1.4.1.ready")
if(NOT EXISTS "${_mvk_marker}")
    message(FATAL_ERROR
        "No SDK prepared for iOS in:\n  ${NFSMW_SDK}\n"
        "Run first:  python3 tools/ios/prepare_sdk.py")
endif()
file(READ "${NFSMW_SDK}/include/rex/platform.h" _platform_h)
if(NOT _platform_h MATCHES "REX_PLATFORM_IOS")
    message(FATAL_ERROR "The SDK lacks the iOS patches. Run: python3 tools/ios/prepare_sdk.py")
endif()
file(STRINGS "${_mvk_marker}" _mvk_rel LIMIT_COUNT 1)
set(NFSMW_MOLTENVK_FW "${NFSMW_SDK}/.nfsmw-ios/MoltenVK/${_mvk_rel}/ios-arm64/MoltenVK.framework")
if(NOT EXISTS "${NFSMW_MOLTENVK_FW}/MoltenVK")
    message(FATAL_ERROR "Cannot find ${NFSMW_MOLTENVK_FW}/MoltenVK")
endif()

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
# Library paths are relative from the start (@rpath, @loader_path), not the
# build folder's: the app gets copied to the device.
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)

set(REXGLUE_ENABLE_TRACY OFF CACHE BOOL "" FORCE)
set(REXGLUE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(REXGLUE_USE_VULKAN ON CACHE BOOL "" FORCE)
set(REXGLUE_USE_D3D12 OFF CACHE BOOL "" FORCE)
set(REXGLUE_ENABLE_DESKTOP_SDL_BACKENDS OFF CACHE BOOL "" FORCE)

# The presenter's FSR 1.0 and CAS, as on Android (see there for why). Across
# the whole tree except the generated code.
add_compile_definitions(
    $<$<NOT:$<STREQUAL:$<TARGET_PROPERTY:NAME>,nfsmw_recomp>>:REX_HAS_FIDELITYFX_SDK=1>)

add_subdirectory("${NFSMW_SDK}" rexglue-sdk)

# Include paths only, as on Android: rexui and rexcore are OBJECT libraries and
# linking them would duplicate global state (the cvar registry).
add_library(nfsmw_headers INTERFACE)
target_include_directories(nfsmw_headers INTERFACE
    $<TARGET_PROPERTY:imgui,INTERFACE_INCLUDE_DIRECTORIES>)
target_link_libraries(nfsmw_headers INTERFACE
    renderdoc
    Vulkan::Headers
    GPUOpen::VulkanMemoryAllocator
    spirv-tools-headers)

# -----------------------------------------------------------------------------
#  Generated game code, if any
# -----------------------------------------------------------------------------
set(NFSMW_WITH_GAME OFF)
if(EXISTS "${NFSMW_GEN_DIR}/sources.cmake")
    set(NFSMW_WITH_GAME ON)
    include("${NFSMW_GEN_DIR}/sources.cmake")

    add_library(nfsmw_recomp STATIC ${GENERATED_SOURCES})
    target_include_directories(nfsmw_recomp PRIVATE
        "${NFSMW_REPO}/app"
        "${NFSMW_REPO}/common/src"
        "${NFSMW_GEN_DIR}")
    target_link_libraries(nfsmw_recomp PUBLIC rex::runtime nfsmw_headers)
    rexglue_apply_target_settings(nfsmw_recomp)
    # As on desktop and Android: PCH, and line tables only for debug info,
    # which matters with a million generated lines.
    target_precompile_headers(nfsmw_recomp PRIVATE "${NFSMW_GEN_DIR}/nfsmw_pch.h")
    target_compile_options(nfsmw_recomp PRIVATE -gline-tables-only -Wno-unused-variable)
    set_property(GLOBAL APPEND PROPERTY JOB_POOLS recomp=${NFSMW_JOBS_RECOMP})
    set_target_properties(nfsmw_recomp PROPERTIES JOB_POOL_COMPILE recomp)
    message(STATUS "NFSMW: with the game (${NFSMW_GEN_DIR})")
else()
    message(STATUS "NFSMW: no generated code in ${NFSMW_GEN_DIR}: probe only. "
                   "For the game: python3 tools/ios/generate_code.py")
endif()

# -----------------------------------------------------------------------------
#  The app
# -----------------------------------------------------------------------------
set(NFSMW_VERSION "0.5.0")
set(NFSMW_VERSION_CODE "8")
# The name under the icon: the full title does not fit on the home screen.
set(NFSMW_DISPLAY_NAME "NFS Most Wanted")
set(NFSMW_IOS_MIN "${CMAKE_OSX_DEPLOYMENT_TARGET}")
set(NFSMW_EXECUTABLE "NFSMW")
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
               "${CMAKE_CURRENT_BINARY_DIR}/Info.plist" @ONLY)

add_executable(nfsmw MACOSX_BUNDLE
    src/ios_main.mm
    src/launcher.mm
    src/hud_editor.mm
    src/save_manager.mm
    src/save_import.cpp
    src/save_convert.cpp
    src/boot_trace.cpp
    src/probe.cpp
    src/probe_apple.mm
    src/probe_memory.cpp)
set_target_properties(nfsmw PROPERTIES
    OUTPUT_NAME "${NFSMW_EXECUTABLE}"
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_BINARY_DIR}/Info.plist"
    # @loader_path, not @executable_path: inside LiveContainer the process
    # executable is LiveContainer's, and @executable_path would point at ITS
    # bundle. For the app's own executable, in a normal launch, they match.
    INSTALL_RPATH "@loader_path/Frameworks")
target_compile_options(nfsmw PRIVATE $<$<COMPILE_LANGUAGE:OBJCXX>:-fobjc-arc>)
target_include_directories(nfsmw PRIVATE "${NFSMW_SDK}/include")
target_link_libraries(nfsmw PRIVATE rex::runtime nfsmw_headers
    "-framework Foundation" "-framework UIKit" "-framework Metal" "-framework MetalFX" "-framework QuartzCore" "-framework CoreImage"
    "-framework UniformTypeIdentifiers" z)
# The Xbox 360 language and country of the edition. With the game, from
# ios/generated/edicion.json (tools/ios/generate_code.py); without it, USA's,
# the edition this port targets (tools/ediciones/ediciones.json).
set(NFSMW_GAME_LANGUAGE "1")
set(NFSMW_GAME_COUNTRY "103")
get_filename_component(NFSMW_GENERATED "${NFSMW_GEN_DIR}/.." ABSOLUTE)
set(NFSMW_EDITION "")
if(NFSMW_WITH_GAME AND EXISTS "${NFSMW_GENERATED}/edicion.json")
    file(READ "${NFSMW_GENERATED}/edicion.json" _edition)
    string(JSON NFSMW_GAME_LANGUAGE GET "${_edition}" idioma)
    string(JSON NFSMW_GAME_COUNTRY GET "${_edition}" pais)
    string(JSON _is_reference GET "${_edition}" referencia)
    if(NOT _is_reference)
        string(JSON NFSMW_EDITION GET "${_edition}" tabla)
    endif()
endif()
target_compile_definitions(nfsmw PRIVATE
    REXGLUE_BUILD_CONFIG="$<CONFIG>"
    NFSMW_WITH_GAME=$<BOOL:${NFSMW_WITH_GAME}>
    NFSMW_GAME_LANGUAGE="${NFSMW_GAME_LANGUAGE}"
    NFSMW_GAME_COUNTRY="${NFSMW_GAME_COUNTRY}")

if(NFSMW_WITH_GAME)
    # The sources that name game functions and data BY ADDRESS. The addresses
    # are those of the reference edition (PAL Spain): for it they compile as
    # they are; for another, translated (below), exactly as on Android.
    #
    # common/src: the game-side code shared with the original project
    # (render_targets.cpp is its Android port's render-target hook, unchanged
    # but for the iOS fixes marked in it). game_hooks.cpp is the iOS copy of
    # the Android ganchos.cpp (Apple's futex).
    set(NFSMW_GAME_SOURCES
        "${CMAKE_CURRENT_SOURCE_DIR}/src/game_app.cpp"
        "${CMAKE_CURRENT_SOURCE_DIR}/src/game_hooks.cpp"
        "${NFSMW_REPO}/common/src/render_targets.cpp"
        "${NFSMW_REPO}/common/src/nfsmw_menu.cpp")

    if(NFSMW_EDITION)
        # Every address in those sources and their headers is mapped to the
        # edition's with its table (tools/ediciones/<edition>/direcciones.tsv),
        # and the copies are compiled. A hook at the Spanish address would land,
        # in another edition, in the middle of another function.
        find_package(Python3 REQUIRED COMPONENTS Interpreter)
        set(_translated "${NFSMW_GENERATED}/edicion/src")
        file(GLOB _headers CONFIGURE_DEPENDS
            "${CMAKE_CURRENT_SOURCE_DIR}/src/*.h" "${NFSMW_REPO}/common/src/*.h")
        set(_sources "")
        set(_outputs "")
        foreach(_origin IN LISTS NFSMW_GAME_SOURCES _headers)
            get_filename_component(_name "${_origin}" NAME)
            list(APPEND _outputs "${_translated}/${_name}")
            if(_origin IN_LIST NFSMW_GAME_SOURCES)
                list(APPEND _sources "${_translated}/${_name}")
            endif()
        endforeach()
        add_custom_command(
            OUTPUT ${_outputs}
            COMMAND Python3::Interpreter "${NFSMW_REPO}/tools/ediciones/ediciones.py"
                    fuentes "${NFSMW_EDITION}" "${_translated}"
                    ${NFSMW_GAME_SOURCES} ${_headers}
            DEPENDS ${NFSMW_GAME_SOURCES} ${_headers}
                    "${NFSMW_REPO}/tools/ediciones/ediciones.py"
                    "${NFSMW_REPO}/tools/ediciones/${NFSMW_EDITION}/direcciones.tsv"
            COMMENT "NFSMW: hook addresses to the '${NFSMW_EDITION}' edition"
            VERBATIM)
        target_sources(nfsmw PRIVATE ${_outputs})
        # Ahead of app/src: whoever includes nfsmw_app.h gets the translated
        # one. And the originals' folder, for what they include by relative
        # path (audio/...), which the copy no longer finds on its own.
        target_include_directories(nfsmw PRIVATE "${_translated}")
        set(NFSMW_GAME_SOURCES ${_sources})
        message(STATUS "NFSMW: edition '${NFSMW_EDITION}', hooks translated in ${_translated}")
    else()
        message(STATUS "NFSMW: reference edition (PAL Spain)")
    endif()

    # windowed_app_main_sdl.cpp is NOT compiled: ios_main.mm is the entry
    # point. Outside Android the SDK is not in "apps in a library" mode, so
    # REX_DEFINE_APP (game_app.cpp) defines GetWindowedAppCreator(), which
    # ios_main.mm calls.
    # Black Edition content needs a larger record pool than the game has
    # (src/game_pool.cpp): USA addresses, plus edits to the generated code that
    # tools/ios/generate_code.py makes (tools/ios/patch_game_pool.py). Without
    # them, starting the career freezes with Black Edition on.
    if(NFSMW_EDITION STREQUAL "usa")
        execute_process(
            COMMAND "${Python3_EXECUTABLE}" "${NFSMW_REPO}/tools/ios/patch_game_pool.py" --status
            OUTPUT_VARIABLE _pool OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(NOT _pool MATCHES "^\\[pool\\] applied")
            message(FATAL_ERROR "NFSMW: the generated code lacks the record pool edits "
                "(${_pool}). Run: python3 tools/ios/patch_game_pool.py")
        endif()
        target_sources(nfsmw PRIVATE src/game_pool.cpp src/game_save_id.cpp)
        message(STATUS "NFSMW: ${_pool}")
        # Extra Options features (src/game_extra_options.cpp), with their edits
        # to the generated code (tools/ios/patch_game_extra_options.py).
        execute_process(
            COMMAND "${Python3_EXECUTABLE}" "${NFSMW_REPO}/tools/ios/patch_game_extra_options.py"
                    --status
            OUTPUT_VARIABLE _extra OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(NOT _extra MATCHES "^\\[extra-options\\] applied")
            message(FATAL_ERROR "NFSMW: the generated code lacks the Extra Options edits "
                "(${_extra}). Run: python3 tools/ios/patch_game_extra_options.py")
        endif()
        target_sources(nfsmw PRIVATE src/game_extra_options.cpp src/render_probe.cpp
            src/game_scene_size.cpp src/game_state.cpp src/game_job_wait.cpp src/game_audio_budget.cpp src/game_gpr_helpers.cpp src/adaptive_qos.cpp src/frame_clock.cpp src/native_draw_census.cpp
            src/native_metal_probe.mm src/native_renderer.mm)
# Line tables for the native renderer (no code change): Time Profiler samples
# from a device trace map to source lines (dsymutil the app's NFSMW).
set_source_files_properties(src/native_renderer.mm PROPERTIES COMPILE_OPTIONS -gline-tables-only)
        message(STATUS "NFSMW: ${_extra}")
        execute_process(
            COMMAND "${Python3_EXECUTABLE}" "${NFSMW_REPO}/tools/ios/patch_game_constant_copies.py"
                    --status
            RESULT_VARIABLE _copies_result
            OUTPUT_VARIABLE _copies OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(NOT _copies_result EQUAL 0 OR NOT _copies MATCHES "^\\[constant-copies\\] applied")
            message(FATAL_ERROR "NFSMW: generated code lacks native constant copy edits. "
                "Run: python3 tools/ios/patch_game_constant_copies.py")
        endif()
        message(STATUS "NFSMW: ${_copies}")
        target_sources(nfsmw_recomp PRIVATE src/game_constant_copies.h)
        execute_process(
            COMMAND "${Python3_EXECUTABLE}" "${NFSMW_REPO}/tools/ios/patch_game_transform_copies.py"
                    --status
            RESULT_VARIABLE _transforms_result
            OUTPUT_VARIABLE _transforms OUTPUT_STRIP_TRAILING_WHITESPACE)
        if(NOT _transforms_result EQUAL 0 OR NOT _transforms MATCHES "^\\[transform-copies\\] applied")
            message(FATAL_ERROR "NFSMW: generated code lacks native transform copy edits. "
                "Run: python3 tools/ios/patch_game_transform_copies.py")
        endif()
        message(STATUS "NFSMW: ${_transforms}")
        target_sources(nfsmw_recomp PRIVATE src/game_transform_copies.h)
    else()
        message(WARNING "NFSMW: no larger record pool for this edition; with Black "
            "Edition on (--black_edition), starting the career may freeze")
    endif()

    target_sources(nfsmw PRIVATE
        ${NFSMW_GAME_SOURCES}
        src/audio/coreaudio_driver.mm
        src/achievements_export.cpp
        src/battery.mm
        src/gpu_capture.mm
        src/ingame_options.mm
        src/display_rate.mm
        src/lifecycle.mm
        src/memory_report.mm
        src/touch_controls.mm
        "${NFSMW_SDK}/src/ui/rex_app.cpp")
    target_include_directories(nfsmw PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
        "${NFSMW_REPO}/common/src"
        "${NFSMW_GEN_DIR}"
        "${NFSMW_SDK}/src/ui")
    target_link_libraries(nfsmw PRIVATE nfsmw_recomp
        "-framework AudioToolbox" "-framework AVFoundation" "-framework GameController"
        "-framework Metal" "-framework QuartzCore" "-framework CoreImage")

endif()

# The plugin is not linked: the SDK loads it with dlopen. Building it is enough.
add_dependencies(nfsmw rexgpu-xenos)

# -----------------------------------------------------------------------------
#  Packaging: the libraries into Frameworks/, and signing
#
#  Ad-hoc signature (no certificate): LiveContainer re-signs with its own on
#  install. Inside LiveContainer the entitlements that count are
#  LiveContainer's, not the app's; nfsmw.entitlements is applied anyway in
#  case the app is installed on its own.
# -----------------------------------------------------------------------------
#
#  A target of its own that runs on every build, not a POST_BUILD of nfsmw: a
#  POST_BUILD runs only when the executable relinks, so a change only in the
#  SDK (librexgpu-xenos, librexruntime) shipped the old library.
# -----------------------------------------------------------------------------
set(NFSMW_NATIVE_SHADERS_DIR "" CACHE PATH
    "Native renderer bring-up: folder of .metallib shaders to bundle (local test builds only)")
set(_app "$<TARGET_BUNDLE_DIR:nfsmw>")
set(_fw "${_app}/Frameworks")
add_custom_target(nfsmw_package ALL
    COMMAND ${CMAKE_COMMAND} -E make_directory "${_fw}"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "$<TARGET_FILE:rexruntime>" "$<TARGET_FILE:rexgpu-xenos>" "${_fw}/"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${NFSMW_MOLTENVK_FW}" "${_fw}/MoltenVK.framework"
    # The app icon: the asset catalog compiled into Assets.car and the
    # AppIcon*.png files that LiveContainer and the home screen show. Its
    # Info.plist keys are already in Info.plist.in.
    COMMAND xcrun actool "${CMAKE_CURRENT_SOURCE_DIR}/resources/Assets.xcassets"
            --compile "${_app}" --platform iphoneos
            --minimum-deployment-target "${CMAKE_OSX_DEPLOYMENT_TARGET}"
            --target-device iphone --target-device ipad --app-icon AppIcon
            --output-partial-info-plist "${CMAKE_CURRENT_BINARY_DIR}/actool-partial.plist"
            --output-format human-readable-text --errors --warnings
    # Native renderer bring-up: the Metal shader libraries built by
    # tools/native/build_shaders.sh from your own game files, for local test
    # builds only (-DNFSMW_NATIVE_SHADERS_DIR=...; empty: none).
    COMMAND ${CMAKE_COMMAND} -E $<IF:$<BOOL:${NFSMW_NATIVE_SHADERS_DIR}>,copy_directory,true>
            ${NFSMW_NATIVE_SHADERS_DIR} "${_app}/NativeShaders"
    # codesign will not sign files with extended attributes ("resource fork,
    # Finder information, or similar detritus"): the MoltenVK tar and macOS'
    # provenance tagging bring them.
    COMMAND xattr -cr "${_app}"
    COMMAND codesign --force --sign - --timestamp=none "${_fw}/MoltenVK.framework"
    COMMAND codesign --force --sign - --timestamp=none
            "${_fw}/$<TARGET_FILE_NAME:rexruntime>" "${_fw}/$<TARGET_FILE_NAME:rexgpu-xenos>"
    COMMAND codesign --force --sign - --timestamp=none
            --entitlements "${CMAKE_CURRENT_SOURCE_DIR}/nfsmw.entitlements" "${_app}"
    COMMENT "NFSMW: packaging and signing NFSMW.app"
    VERBATIM)
add_dependencies(nfsmw_package nfsmw rexruntime rexgpu-xenos)

# The .ipa: Payload/NFSMW.app zipped. This is what gets imported into
# LiveContainer (or SideStore).
add_custom_target(ipa
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${CMAKE_CURRENT_BINARY_DIR}/ipa"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/ipa/Payload"
    COMMAND ditto "${_app}" "${CMAKE_CURRENT_BINARY_DIR}/ipa/Payload/NFSMW.app"
    COMMAND ${CMAKE_COMMAND} -E rm -f "${CMAKE_CURRENT_BINARY_DIR}/NFSMW.ipa"
    COMMAND ${CMAKE_COMMAND} -E chdir "${CMAKE_CURRENT_BINARY_DIR}/ipa"
            ditto -c -k --sequesterRsrc --keepParent Payload "${CMAKE_CURRENT_BINARY_DIR}/NFSMW.ipa"
    # A handy copy in the repository (ios/build/ is in .gitignore). It is a zip
    # already signed inside: iCloud's attributes do not affect it.
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_SOURCE_DIR}/build"
    COMMAND ${CMAKE_COMMAND} -E copy "${CMAKE_CURRENT_BINARY_DIR}/NFSMW.ipa"
            "${CMAKE_CURRENT_SOURCE_DIR}/build/NFSMW.ipa"
    COMMENT "NFSMW: NFSMW.ipa"
    VERBATIM)
add_dependencies(ipa nfsmw_package)
