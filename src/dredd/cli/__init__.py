"""CLI de dredd (N-DREDD-04: antes era un cli.py de 1.896 líneas).

Los comandos viven en un módulo por área (configuracion, evaluacion, github, exportacion,
analisis); acá se registran en las apps, en el orden en que aparecen en `dredd --help`.
"""

from dredd.cli._base import app, config_app, evaluate_app, github_app, moodle_app
from dredd.cli.configuracion import (  # noqa: F401
    cmd_config_add_entrega,
    cmd_config_preset,
    cmd_config_remove_entrega,
    cmd_config_set_check,
    cmd_config_show,
    cmd_config_validate,
    cmd_init,
)
from dredd.cli.evaluacion import (  # noqa: F401
    cmd_cohort_bench,
    cmd_eval,
    cmd_eval_shielded,
    cmd_eval_stability,
    cmd_evaluate_clean,
    cmd_evaluate_run,
    cmd_late_penalty,
    cmd_rerun,
    cmd_smith_adversary,
    cmd_typology,
    ejecutar_evaluacion,
    ejecutar_limpieza_evaluaciones,
)
from dredd.cli.github import (  # noqa: F401
    cmd_audit_git,
    cmd_comment,
    cmd_diff_submission,
    cmd_git_forensics,
    cmd_github_clone,
    cmd_pr_fix,
)
from dredd.cli.exportacion import (  # noqa: F401
    cmd_dashboard,
    cmd_export,
    cmd_export_feedback,
    cmd_export_guarani,
    cmd_export_report,
    cmd_moodle_export,
    cmd_moodle_ingest,
    cmd_report_template,
    cmd_sanitize_output,
)
from dredd.cli.analisis import (  # noqa: F401
    cmd_audit_makefile,
    cmd_audit_versions,
    cmd_cluster_errors,
    cmd_doctor,
    cmd_map,
    cmd_multiplex,
    cmd_plagiarism,
    cmd_plagiarism_historical,
    fuzz_gen,
    oral_guide,
)

# Registro de los comandos: el orden es el que lista `--help`.
app.command('init')(cmd_init)
app.command('eval')(cmd_eval)
app.command('clean-eval', hidden=True)(cmd_evaluate_clean)
evaluate_app.command('clean')(cmd_evaluate_clean)
evaluate_app.command('run')(cmd_evaluate_run)
github_app.command('clone')(cmd_github_clone)
github_app.command('comment')(cmd_comment)
app.command('plagiarism')(cmd_plagiarism)
github_app.command('pr-fix')(cmd_pr_fix)
app.command('map')(cmd_map)
moodle_app.command('ingest')(cmd_moodle_ingest)
app.command('export')(cmd_export)
app.command('export-report')(cmd_export_report)
moodle_app.command('export')(cmd_moodle_export)
app.command('fuzz-gen')(fuzz_gen)
app.command('oral-guide')(oral_guide)
app.command('multiplex')(cmd_multiplex)
config_app.command('show')(cmd_config_show)
config_app.command('add-entrega')(cmd_config_add_entrega)
config_app.command('remove-entrega')(cmd_config_remove_entrega)
config_app.command('set-check')(cmd_config_set_check)
config_app.command('validate')(cmd_config_validate)
config_app.command('preset')(cmd_config_preset)
app.command('doctor')(cmd_doctor)
app.command('rerun')(cmd_rerun)
moodle_app.command('export-guarani')(cmd_export_guarani)
app.command('export-guarani')(cmd_export_guarani)
app.command('serve-dashboard')(cmd_dashboard)
app.command('dashboard')(cmd_dashboard)
app.command('audit-git')(cmd_audit_git)
app.command('git-forensics')(cmd_git_forensics)
app.command('notify-batch')(cmd_export_feedback)
app.command('export-feedback')(cmd_export_feedback)
app.command('plagiarism-historical')(cmd_plagiarism_historical)
app.command('diff-revision')(cmd_diff_submission)
app.command('diff-submission')(cmd_diff_submission)
app.command('late-penalty')(cmd_late_penalty)
app.command('audit-makefile')(cmd_audit_makefile)
app.command('cluster-errors')(cmd_cluster_errors)
app.command('audit-versions')(cmd_audit_versions)
app.command('typology')(cmd_typology)
app.command('eval-stability')(cmd_eval_stability)
app.command('cohort-bench')(cmd_cohort_bench)
app.command('smith-adversary')(cmd_smith_adversary)
app.command('eval-shielded')(cmd_eval_shielded)
app.command('report-template')(cmd_report_template)
app.command('sanitize-output')(cmd_sanitize_output)
