#!/bin/sh
set -eu

case "${1:-}" in
    configuration)
        package=Microsoft.Extensions.Configuration
        focus=Microsoft.Extensions.Primitives
        ;;
    injection)
        package=Microsoft.Extensions.DependencyInjection
        focus=Microsoft.Extensions.DependencyInjection.Abstractions
        ;;
    logging)
        package=Microsoft.Extensions.Logging
        focus=Microsoft.Extensions.DependencyInjection.Abstractions
        ;;
    *)
        echo "Usage: $0 configuration|injection|logging" >&2
        exit 2
        ;;
esac

temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT
export DOTNET_CLI_UI_LANGUAGE=en
export DOTNET_NOLOGO=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
project="$temp_dir/Compare.csproj"
cat > "$project" <<XML
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup>
    <PackageReference Include="$package" Version="[8.0.0]" />
  </ItemGroup>
</Project>
XML

dotnet restore "$project" --source https://api.nuget.org/v3/index.json \
    --packages "$temp_dir/packages" --no-cache -p:NuGetAudit=false \
    --verbosity normal
dotnet list "$project" package --include-transitive
dotnet nuget why "$project" "$focus" --framework net8.0

echo "Edges from project.assets.json:"
python3 - "$temp_dir/obj/project.assets.json" <<'PY'
import json
import sys
from pathlib import Path

assets = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
target = assets["targets"]["net8.0"]
names = {key.split("/")[0].lower(): key.lower() for key in target}
for key, package in sorted(target.items()):
    for child in sorted(package.get("dependencies", {})):
        print(f"  {key.lower()} -> {names[child.lower()]}")
PY
