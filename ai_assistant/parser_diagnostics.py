def build_parser_report(parser_result, json_ld_available=False):
    critical_checks = []
    info_checks = []
    developer_checks = []

    def add_critical(field, success, message):
        critical_checks.append({
            "field": field,
            "success": success,
            "message": message,
        })

    def add_info(field, message):
        info_checks.append({
            "field": field,
            "message": message,
        })

    def add_developer(field, success, message):
        developer_checks.append({
            "field": field,
            "success": success,
            "message": message,
        })

    company = parser_result["company"]["value"]
    job = parser_result["job"]["value"]
    location = parser_result["locations"]["value"]
    contacts = parser_result["contacts"]
    application_method = parser_result.get("application_method", "")

    add_critical(
        "Company",
        bool(company),
        "Company detected." if company else "Company not detected.",
    )

    add_critical(
        "Job Title",
        bool(job),
        "Job title detected." if job else "Job title not detected.",
    )

    add_critical(
        "Location",
        bool(location),
        "Location verified." if location else "Location could not be verified.",
    )

    add_critical(
        "Application Method",
        bool(application_method),
        "Application method inferred." if application_method else "Application method unknown.",
    )

    if contacts.get("contact_person"):
        add_info("Contact Person", "Contact person detected.")
    else:
        add_info("Contact Person", "No named recruiter was provided.")

    if contacts.get("contact_email"):
        add_info("Contact Email", "Contact email detected.")
    elif application_method == "job_board":
        add_info("Contact Email",
                 "Application appears to be handled through a job portal.")
    else:
        add_info("Contact Email", "No direct contact email was provided.")

    if contacts.get("contact_phone"):
        add_info("Contact Phone", "Contact phone detected.")
    else:
        add_info("Contact Phone", "No phone number was provided.")

    add_developer(
        "JSON-LD",
        json_ld_available,
        "Structured job metadata available."
        if json_ld_available
        else "No JSON-LD metadata available.",
    )

    passed = sum(1 for check in critical_checks if check["success"])
    total = len(critical_checks)
    percent = round((passed / total) * 100) if total else 0

    if percent == 100:
        quality_label = "Ready to Apply"
        quality_class = "success"
        summary = "The essential job information was detected successfully."
        recommendation = "Review the fields below, then continue."
    elif percent >= 75:
        quality_label = "Needs Review"
        quality_class = "warning"
        summary = "Most essential job information was detected."
        recommendation = "Review and correct the missing field before continuing."
    else:
        quality_label = "Manual Review Required"
        quality_class = "danger"
        summary = "Several essential fields are missing."
        recommendation = "Manually correct the detected fields before creating the application."

    return {
        "critical_checks": critical_checks,
        "info_checks": info_checks,
        "developer_checks": developer_checks,
        "passed": passed,
        "total": total,
        "percent": percent,
        "summary": summary,
        "recommendation": recommendation,
        "quality_label": quality_label,
        "quality_class": quality_class,
    }
