from eeg_core.report.html_report import write_html_report


def run_task(output_dir, title, context):
    return write_html_report(output_dir, title, context)

