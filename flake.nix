{
  description = "Development environment with Python, Node.js, Poetry, and build tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

        ## Check if we're on WSL
        isWSL = builtins.pathExists /proc/sys/fs/binfmt_misc/WSLInterop;

        python = pkgs.python312.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          pytest
          ruff
          black
          cleo
          uvicorn
          python-socketio
          fastapi
          python-dotenv
        ]);

        nodejs = pkgs.nodejs_22;

        poetryApp = mkPoetryApplication {
          projectDir = ./.;
          python = pkgs.python312;
          # preferWheels = true;
          extras = [ ];
          # overrides = (self: super: {
          #   # inherit (pkgs.python312.pkgs) playwright flit-core;
          # });
          overrides = defaultPoetryOverrides.extend (self: super: {
            inherit (pkgs.python312.pkgs) ruff;
            types-typed-ast = null; # super.types-typed-ast or null;
            # ruff = null;
            # uvicorn = null;
          });
        };

        ## Poetry 1.8.x
        poetry = pkgs.poetry;

        baseTools = with pkgs; [
          uv
          python
          nodejs
          poetry
          pre-commit
        ];

        ## Build essential tools
        buildTools = with pkgs; [
          gcc
          gnumake
          cmake
          pkg-config
          autoconf
          automake
          libtool
        ];

        ## Optional WSL-specific tools
        wslTools = with pkgs; lib.optionals isWSL [
          netcat-gnu
        ];

      in {

        apps.default = {
          type = "app";
          program = "${poetryApp}/bin/openhands";
        };

        apps.poetry = {
          type = "app";
          program = "${poetryApp}/bin/$1";
        };

        packages.default = poetryApp;

        devShells.default = pkgs.mkShellNoCC {
          buildInputs = baseTools ++ buildTools ++ wslTools;

          venvDir = "./.venv";
          nativeBuildInputs = [ python.pkgs.venvShellHook ];

          postShellHook = ''
            echo "Development environment loaded!"
            echo "Python: $(python --version)"
            echo "Node.js: $(node --version)"
            echo "Poetry: $(poetry --version)"
            echo "GCC: $(gcc --version | head -n1)"
            echo "UV: $(uv --version)"
            echo "Ruff: $(ruff --version)"
            echo "Black: $(black --version)"
            ${if isWSL then ''echo "WSL detected - netcat included"'' else ""}
            echo ""
            echo "All development dependencies are ready."
          '';

          ## Set up environment variables
          PYTHON = "${python}/bin/python";
          NODE_PATH = "${nodejs}/lib/node_modules";

          ## Ensure Python can find its headers
          C_INCLUDE_PATH = "${python}/include/${python.libPrefix}";
          CPLUS_INCLUDE_PATH = "${python}/include/${python.libPrefix}";
          
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [stdenv.cc.cc.lib ffmpeg]);

          # postShellHook = ''
          #   export SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.48-nikolaik
          #   export SANDBOX_VOLUMES="$(pwd):/workspace:rw"
          #   export SANDBOX_USER_ID=$(id -u)
          #   if [[ -f .env ]]; then
          #     set -a
          #     source .env
          #     set +a
          #   fi
          # '';

        };
      });
}
