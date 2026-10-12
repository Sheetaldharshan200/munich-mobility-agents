# Reference solutions (presenter only, never installed)

One worked solution per agent, produced on 2026-10-12 against the loaded snapshot: the queries and the finished Dash app on the shared look. Use them in rehearsal to compare what the live agent produced, to recover a demo machine quickly, or to see the intended shape of each dashboard.

They are deliberately not part of the skills. The agents design their SQL and build their dashboards live; handing them these files would turn the demo into file copying.

Deploy one by hand if needed: scaffold with `app_create_exasol_dashboard{name, profile_name: "starter-kit"}`, then `app_put_files` with `app.py`, `munich_ui.py` (from `skill/_shared/`), `queries/*` and the requirements line from the playbook, then `app_deploy_draft`.
