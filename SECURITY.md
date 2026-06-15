# Security Policy

## Supported versions

This project is developed on the `main` branch, and security fixes are applied
to the latest release. Please make sure you are running the most recent version
before reporting an issue.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report privately through GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability):
go to the repository's **Security** tab and click **Report a vulnerability**.

Please include:

- A description of the vulnerability and its impact.
- Steps to reproduce, or a proof of concept.
- The exporter version and environment (BOINC client version, OS, deployment
  method).

You can expect an initial acknowledgement within a few days. We will keep you
informed about progress toward a fix and may ask for additional details.

## Scope and security notes

BOINC Exporter connects to a BOINC client over the **GUI RPC interface**
(TCP/31416) and exposes a Prometheus `/metrics` endpoint. Keep the following in
mind when deploying:

- The GUI RPC password is supplied via the `BOINC_PASSWORD` environment
  variable. Treat it as a secret — do not commit it to version control or bake
  it into images. The exporter never logs the password.
- The `/metrics` endpoint is unauthenticated by design (standard for Prometheus
  exporters). Do not expose it directly to untrusted networks; restrict access
  with your firewall, reverse proxy, or network policy.
- `allow_remote_gui_rpc` in the BOINC client widens the RPC attack surface.
  Enable it only on trusted networks and prefer connecting over localhost or a
  private network where possible.

Reports about insecure default configurations or documentation that could lead
users into an unsafe setup are also welcome.
