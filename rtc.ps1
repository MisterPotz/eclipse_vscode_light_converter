param (
    [Parameter(Mandatory, HelpMessage="path to eclipse projects folder")]
    [string]
    $EclipseProject,
    [Parameter(Mandatory, HelpMessage="list folders of nested eclipse projects")]
    [string]
    $SubProjects,
    [Parameter(Mandatory, HelpMessage="path to .p2 repository")]
    [string]
    $P2Path,
    [Parameter(Mandatory, HelpMessage="path to cached parsed dependencies")]
    [string]
    $DepCache
)

python $PSScriptRoot\classpath_installer.py $EclipseProject $SubProjects -cc -p2 $P2Path -cache_path $HOME/.eclipse_vs_code_cache/ -cache_path $DepCache
