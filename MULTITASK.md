# MultitaskContainer

This repository now contains a reproducible GitHub Actions build for an iOS multitasking/container IPA based on the open-source LiveContainer project.

## What it provides

- Imports the upstream LiveContainer source at build time.
- Builds the iOS target on a macOS GitHub Actions runner.
- Packages the resulting application as an unsigned `.ipa` artifact.
- The artifact can be downloaded from the workflow run and signed with your own Apple development signing workflow (for example, Sideloadly).

## Important

This is intentionally a source/build pipeline rather than a checked-in copy of the upstream project. The resulting application is based on upstream LiveContainer, whose project documentation describes multitasking with multiple virtual windows, resizing/scaling, and Picture-in-Picture support. See the upstream project and its license before redistributing builds.

An unsigned IPA cannot be installed directly on a normal iPhone. It needs to be signed for the device/account that will install it.

## Build

The workflow runs automatically when this repository's `main` branch changes, and it can also be started manually from GitHub Actions with **Run workflow**.

The output artifact is named `MultitaskContainer-unsigned-ipa`.

## Upstream project

https://github.com/LiveContainer/LiveContainer
