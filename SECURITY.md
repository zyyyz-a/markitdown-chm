# Security policy

## Trust model

Treat every CHM file as untrusted binary input. `markitdown-chm` parses archives
with `pylibmspack`, reads only content needed for conversion, and never executes
HTML, JavaScript, ActiveX, embedded objects, or CHM navigation commands.

Before rendering, the converter removes active-content elements and inline
event-handler attributes. It also enforces bounded reads for the archive and
each topic, plus limits on member count, topic count, and total HTML bytes.

No parser can guarantee safety against every native-library vulnerability. Run
bulk conversion services with operating-system isolation, current dependencies,
least privilege, memory/CPU limits, and no access to secrets.

## Reporting a vulnerability

Please use GitHub's private security-advisory flow for this repository. Include
a minimal reproducer, affected version, expected impact, and any suggested
mitigation. Do not attach a malicious CHM to a public issue.

