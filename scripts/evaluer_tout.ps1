# Lance toute l'evaluation (equivalent Windows de make reproduce). Les journaux vont dans results/logs.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force results\logs | Out-Null
$py = ".venv\Scripts\python.exe"
$etapes = @(
    @("baseline", @("evaluer", "baseline")),
    @("kasiski", @("evaluer", "kasiski")),
    @("shannon", @("evaluer", "shannon")),
    @("llm_tres_petit", @("evaluer", "llm", "--modele", "tres_petit")),
    @("llm_petit", @("evaluer", "llm", "--modele", "petit"))
)
foreach ($e in $etapes) {
    $debut = Get-Date
    & $py -m vigenere_squad.cli @($e[1]) *> "results\logs\$($e[0]).log"
    "$($e[0]) fini en $([int]((Get-Date) - $debut).TotalSeconds) s" | Add-Content results\logs\etapes.log
}
"TOUT_FINI" | Add-Content results\logs\etapes.log
