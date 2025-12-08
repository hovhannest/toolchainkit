import yaml
from pathlib import Path

configs = {
    # 1. Basic Compilers & Build Tools
    "toolchainkit_1.yaml": {
        "description": "LLVM + Ninja (Release)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "build": {"types": ["Release"], "parallel_jobs": "auto"},
    },
    "toolchainkit_2.yaml": {
        "description": "GCC + Make (Release)",
        "toolchain": {
            "name": "gcc-13",
            "type": "gcc",
            "version": "13.2.0",
            "stdlib": "libstdc++",
        },
        "defaults": {
            "toolchain": "gcc-13",
            "build_type": "Release",
            "generator": "Make",
        },
        "build": {"types": ["Release"], "parallel_jobs": "auto"},
    },
    "toolchainkit_3.yaml": {
        "description": "MSVC + MSBuild (Release)",
        "toolchain": {
            "name": "msvc-latest",
            "type": "msvc",
            "version": "latest",
            "stdlib": "msvc",
        },
        "defaults": {
            "toolchain": "msvc-latest",
            "build_type": "Release",
            "generator": "MSBuild",
        },
        "build": {"types": ["Release"], "parallel_jobs": "auto"},
    },
    "toolchainkit_4.yaml": {
        "description": "MSVC + Ninja (Release)",
        "toolchain": {
            "name": "msvc-latest",
            "type": "msvc",
            "version": "latest",
            "stdlib": "msvc",
        },
        "defaults": {
            "toolchain": "msvc-latest",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "build": {"types": ["Release"], "parallel_jobs": "auto"},
    },
    # 2. Build Types (LLVM + Ninja)
    "toolchainkit_5.yaml": {
        "description": "LLVM + Debug",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "generator": "Ninja",
        },
        "build": {"types": ["Debug"], "parallel_jobs": "auto"},
    },
    "toolchainkit_6.yaml": {
        "description": "LLVM + RelWithDebInfo",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "RelWithDebInfo",
            "generator": "Ninja",
        },
        "build": {"types": ["RelWithDebInfo"], "parallel_jobs": "auto"},
    },
    "toolchainkit_7.yaml": {
        "description": "LLVM + MinSizeRel",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "MinSizeRel",
            "generator": "Ninja",
        },
        "build": {"types": ["MinSizeRel"], "parallel_jobs": "auto"},
    },
    # 3. Allocators (LLVM + Ninja + Release)
    "toolchainkit_8.yaml": {
        "description": "LLVM + jemalloc",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "jemalloc"}],
    },
    "toolchainkit_9.yaml": {
        "description": "LLVM + mimalloc",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "mimalloc"}],
    },
    "toolchainkit_10.yaml": {
        "description": "LLVM + tbbmalloc",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "tbbmalloc"}],
    },
    "toolchainkit_11.yaml": {
        "description": "LLVM + tcmalloc (Linux/macOS only)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "tcmalloc"}],
    },
    "toolchainkit_12.yaml": {
        "description": "LLVM + snmalloc",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "snmalloc"}],
    },
    # 4. Sanitizers (LLVM + Ninja + Debug)
    "toolchainkit_13.yaml": {
        "description": "LLVM + Address Sanitizer",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "generator": "Ninja",
        },
        "layers": [{"type": "sanitizer", "name": "address"}],
    },
    "toolchainkit_14.yaml": {
        "description": "LLVM + Memory Sanitizer",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "generator": "Ninja",
        },
        "layers": [{"type": "sanitizer", "name": "memory"}],
    },
    "toolchainkit_15.yaml": {
        "description": "LLVM + Thread Sanitizer",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "generator": "Ninja",
        },
        "layers": [{"type": "sanitizer", "name": "thread"}],
    },
    "toolchainkit_16.yaml": {
        "description": "LLVM + Undefined Behavior Sanitizer",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Debug",
            "generator": "Ninja",
        },
        "layers": [{"type": "sanitizer", "name": "undefined"}],
    },
    # 5. Cross Compilation
    "toolchainkit_17.yaml": {
        "description": "Android (arm64)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "cross": {
            "enabled": True,
            "target": "android",
            "android": {
                "abi": "arm64-v8a",
                "api_level": 30,
                "ndk_path": "/opt/android-ndk",
            },
        },
    },
    "toolchainkit_18.yaml": {
        "description": "iOS",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Xcode",
        },
        "cross": {
            "enabled": True,
            "target": "ios",
            "ios": {"platform": "iphoneos", "deployment_target": "15.0"},
        },
    },
    "toolchainkit_19.yaml": {
        "description": "Raspberry Pi",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "cross": {
            "enabled": True,
            "target": "raspberry-pi",
            "raspberry_pi": {"arch": "aarch64", "sysroot": "/opt/sysroot/pi"},
        },
    },
    # 6. Advanced/Mixed
    "toolchainkit_20.yaml": {
        "description": "LLVM + libc++ + Ninja + mimalloc (High Performance Cross-Platform)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "mimalloc"}],
    },
    "toolchainkit_21.yaml": {
        "description": "GCC + libstdc++ + Make + jemalloc (Linux Standard)",
        "toolchain": {
            "name": "gcc-13",
            "type": "gcc",
            "version": "13.2.0",
            "stdlib": "libstdc++",
        },
        "defaults": {
            "toolchain": "gcc-13",
            "build_type": "Release",
            "generator": "Make",
        },
        "layers": [{"type": "allocator", "name": "jemalloc"}],
    },
    "toolchainkit_22.yaml": {
        "description": "MSVC + MSBuild + tbbmalloc (Windows Enterprise)",
        "toolchain": {
            "name": "msvc-latest",
            "type": "msvc",
            "version": "latest",
            "stdlib": "msvc",
        },
        "defaults": {
            "toolchain": "msvc-latest",
            "build_type": "Release",
            "generator": "MSBuild",
        },
        "layers": [{"type": "allocator", "name": "tbbmalloc"}],
    },
    "toolchainkit_23.yaml": {
        "description": "LLVM + Xcode + jemalloc (macOS Native)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Xcode",
        },
        "layers": [{"type": "allocator", "name": "jemalloc"}],
    },
    "toolchainkit_24.yaml": {
        "description": "GCC + Ninja + tcmalloc (Linux High Performance Server)",
        "toolchain": {
            "name": "gcc-13",
            "type": "gcc",
            "version": "13.2.0",
            "stdlib": "libstdc++",
        },
        "defaults": {
            "toolchain": "gcc-13",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "layers": [{"type": "allocator", "name": "tcmalloc"}],
    },
    # 7. Package Managers
    "toolchainkit_25.yaml": {
        "description": "LLVM + Conan (Default)",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "packages": {"manager": "conan", "conanfile": "conanfile.txt"},
    },
    "toolchainkit_26.yaml": {
        "description": "LLVM + Vcpkg",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "packages": {"manager": "vcpkg", "manifest": "vcpkg.json"},
    },
    "toolchainkit_27.yaml": {
        "description": "LLVM + No Package Manager",
        "toolchain": {
            "name": "llvm-18",
            "type": "llvm",
            "version": "18.1.8",
            "stdlib": "libc++",
        },
        "defaults": {
            "toolchain": "llvm-18",
            "build_type": "Release",
            "generator": "Ninja",
        },
        "packages": None,
    },
}

base_path = Path("d:/workplace/cpp/toolchainkit/examples/01-new-project")

for filename, data in configs.items():
    content = {
        "version": 1,
        "project": {
            "name": "example-project",
            "version": "0.1.0",
            "description": data["description"],
        },
        "toolchains": {
            data["toolchain"]["name"]: {
                "type": data["toolchain"]["type"],
                "version": data["toolchain"]["version"],
                "stdlib": data["toolchain"]["stdlib"],
            }
        },
        "defaults": data["defaults"],
        "build": data.get(
            "build",
            {"types": [data["defaults"]["build_type"]], "parallel_jobs": "auto"},
        ),
    }

    if "packages" in data and data["packages"] is not None:
        content["packages"] = data["packages"]

    if "layers" in data:
        content["toolchains"][data["toolchain"]["name"]]["layers"] = data["layers"]

    if "cross" in data:
        content["cross"] = data["cross"]

    file_path = base_path / filename
    with open(file_path, "w") as f:
        yaml.dump(content, f, sort_keys=False)
    print(f"Generated {filename}")
