param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('trae', 'claude', 'cursor', 'codex', 'zcode', 'generic')]
    [string]$Target,
    [string]$Path = "."
)

$ErrorActionPreference = "Stop"
$dist = Join-Path $PSScriptRoot "..\dist"
if (-not (Test-Path $dist)) {
    Write-Host "还没有生成产物，先运行： python tools\build.py"
    exit 1
}

function Install-Skills([string]$dest) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Get-ChildItem (Join-Path $dist "skills") -Directory | ForEach-Object {
        Copy-Item $_.FullName -Destination $dest -Recurse -Force
        Write-Host "  + $($_.Name)"
    }
}

switch ($Target) {
    'trae' {
        # $Path 指向技能目录，例如 ~/.trae-cn/skills
        $dest = Join-Path (Resolve-Path $Path) ""
        Write-Host "安装到 Trae 技能目录：$dest"
        Install-Skills $dest
    }
    'cursor' {
        $rootPath = (Resolve-Path $Path).Path
        $dest = Join-Path $rootPath "skills\game-dev"
        Write-Host "安装到项目：$rootPath"
        Install-Skills $dest
        $rules = Join-Path $dist "cursor\.cursor\rules"
        $rdest = Join-Path $rootPath ".cursor\rules"
        New-Item -ItemType Directory -Force -Path $rdest | Out-Null
        Get-ChildItem $rules -Filter "*.mdc" | ForEach-Object {
            Copy-Item $_.FullName -Destination $rdest -Force
            Write-Host "  + .cursor/rules/$($_.Name)"
        }
    }
    'codex' {
        $rootPath = (Resolve-Path $Path).Path
        $dest = Join-Path $rootPath "skills\game-dev"
        Write-Host "安装到项目：$rootPath"
        Install-Skills $dest
        $agents = Join-Path $rootPath "AGENTS.md"
        if (Test-Path $agents) {
            Copy-Item (Join-Path $dist "codex\AGENTS.md") -Destination (Join-Path $rootPath "AGENTS.game-dev.md") -Force
            Write-Host "  已存在 AGENTS.md，索引写到 AGENTS.game-dev.md，请手动合并"
        }
        else {
            Copy-Item (Join-Path $dist "codex\AGENTS.md") -Destination $agents -Force
            Write-Host "  + AGENTS.md"
        }
    }
    'zcode' {
        Write-Host "ZCode 走仓库自带的插件市场，不需要复制技能："
        Write-Host "  $(Join-Path $PSScriptRoot '..\marketplace.json')"
        Write-Host ""
        Write-Host "每个插件都带 .zcode-plugin\plugin.json，导入市场即可。"
    }
    'generic' {
        # 任何认 SKILL.md 的宿主：把技能目录直接拷到它的 skills 目录
        $dest = (Resolve-Path $Path).Path
        Write-Host "安装到技能目录：$dest"
        Install-Skills $dest
    }
    'claude' {
        Write-Host "Claude Code 走插件市场安装，先把仓库推到 Git 远程，然后："
        Write-Host ""
        Write-Host "  /plugin marketplace add <你的仓库地址>"
        Write-Host "  /plugin install aaa-game-gdd"
        Write-Host "  /plugin install unity-blender-mcp"
        Write-Host "  /plugin install blender-modeling-craft"
        Write-Host "  /plugin install unity-gameplay-dev"
        Write-Host ""
        Write-Host "清单在仓库根目录的 .claude-plugin\marketplace.json（python tools\build.py 生成）"
    }
}

Write-Host ""
Write-Host "完成。"
