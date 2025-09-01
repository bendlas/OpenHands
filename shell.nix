## From https://github.com/All-Hands-AI/OpenHands/pull/9599#issuecomment-3047285588
{
  pkgs ? import <nixpkgs> {},
  lib ? pkgs.lib,
}:
let
  inherit (pkgs) mkShellNoCC;
  inherit (pkgs.lib) makeLibraryPath;
  py = pkgs.python312;
in
pkgs.mkShellNoCC {
  venvDir = "./.venv";

  buildInputs = with pkgs; [
    niv
    poetry
    uv
    nodejs_22
    (py.withPackages (ps: with ps; [
      pip
      pytest
      ruff
      black
      cleo
    ]))
    py.pkgs.venvShellHook
  ];

  LD_LIBRARY_PATH = lib.makeLibraryPath (with pkgs; [stdenv.cc.cc.lib ffmpeg]);
  # postVenvCreation = ''
  #   unset SOURCE_DATE_EPOCH
  #   pip install -r requirements.txt
  # '';

  postShellHook = ''
    export SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.48-nikolaik
    # export SANDBOX_VOLUMES="$(pwd):/workspace:rw"
    export SANDBOX_USER_ID=$(id -u)
    if [[ -f .env ]]; then
      set -a
      source .env
      set +a
    fi
  '';
}
