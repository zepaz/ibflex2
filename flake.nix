{
  description = "ibflex2 - Python parser for Interactive Brokers Flex XML statements";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        mkDevShell = python:
          let
            pyEnv = python.withPackages (ps: with ps; [
              requests
              pytest
              pytest-cov
              coverage
              mypy
              types-requests
              build
              setuptools
            ]);
          in
          pkgs.mkShell {
            packages = [ pyEnv pkgs.ruff ];
            shellHook = ''
              export PYTHONPATH="$PWD:$PYTHONPATH"
              echo "ibflex2 dev shell (${python.pythonVersion})"
              echo "  pytest                  -- run tests"
              echo "  mypy ibflex tests       -- static analysis"
              echo "  ruff check ibflex tests -- lint"
              echo "  ruff format ibflex tests -- format"
              echo "  python -m build         -- build sdist+wheel"
            '';
          };
      in
      {
        devShells = {
          default = mkDevShell pkgs.python312;
          py312 = mkDevShell pkgs.python312;
          py313 = mkDevShell pkgs.python313;
        };

        packages.default = pkgs.python312Packages.buildPythonPackage {
          pname = "ibflex2";
          version = "1.0.0";
          src = ./.;
          pyproject = true;

          build-system = with pkgs.python312Packages; [
            setuptools
          ];

          dependencies = with pkgs.python312Packages; [
            requests
          ];

          nativeCheckInputs = with pkgs.python312Packages; [
            pytest
            pytest-cov
          ];

          checkPhase = ''
            runHook preCheck
            pytest tests/
            runHook postCheck
          '';

          meta = with pkgs.lib; {
            description = "Parse Interactive Brokers Flex XML reports (maintained fork)";
            homepage = "https://github.com/robcohen/ibflex2";
            license = licenses.mit;
          };
        };
      });
}
