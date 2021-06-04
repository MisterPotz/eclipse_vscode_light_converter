param (
    [Parameter(Mandatory, HelpMessage="path to eclipse projects folder")]
    [string]
    $EclipseProject,
    [Parameter(Mandatory, HelpMessage="list folders of nested eclipse projects")]
    [string]
    $SubProjects,
    [Parameter(Mandatory, HelpMessage="path to .p2 repository")]
    [string]
    $P2Path
)

python $PSScriptRoot\classpath_installer.py $EclipseProject $SubProjects -ce -p2 $P2Path
