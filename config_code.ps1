function RTCode {
    (& "C:\Users\Alexander\Projects\eclipse_vscode_light_converter\rtc.ps1" `
        -EclipseProject "C:\Users\Alexander\Projects\raox"`
        -SubProjects "ru.bmstu.rk9.rao ru.bmstu.rk9.rao.lib ru.bmstu.rk9.rao.ui"`
        -P2Path "C:\Users\Alexander\.p2"`
        -DepCache "C:\Users\Alexander\.eclipse_vs_code_cache" )
}

function RTEclipse {
    (& "C:\Users\Alexander\Projects\eclipse_vscode_light_converter\rte.ps1" `
    -EclipseProject "C:\Users\Alexander\Projects\raox"`
    -SubProjects "ru.bmstu.rk9.rao ru.bmstu.rk9.rao.lib ru.bmstu.rk9.rao.ui"`
    -P2Path "C:\Users\Alexander\.p2" )
}