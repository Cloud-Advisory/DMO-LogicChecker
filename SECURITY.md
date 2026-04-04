# 🔐 Security Policy for DMO‑LogicChecker

## 🛡️ Supported Versions

The **DMO‑LogicChecker** is under active development. Security updates are provided only for the **latest version on the main branch**.

| Version | Supported | Notes |
|--------|-----------|--------|
| Main   | ✔️ | Actively maintained, receives security fixes |
| Releases / Tags | ⚠️ | Critical fixes only, best‑effort |
| Forks | ❌ | Not supported |

---

## 🕳️ Reporting a Vulnerability

We appreciate responsible disclosure of security vulnerabilities.  
Please **do not create public issues or pull requests** for security-related topics.

### 📣 Report via GitHub

All vulnerability reports must be submitted through the **GitHub Security Advisory** workflow:

👉 **https://github.com/Cloud-Advisory/DMO-LogicChecker/security/advisories/new**

This ensures that:

- Your report remains **private**
- Only project maintainers can access it
- We can coordinate securely and efficiently

### 📝 Information to Include

To help us investigate, please provide:

- A clear description of the vulnerability  
- Steps to reproduce  
- Expected vs. actual behavior  
- Potential impact  
- Optional: suggested fix or proof‑of‑concept  

We typically acknowledge receipt within **96 hours**.

---

## 🔒 Responsible Disclosure

We kindly ask you to:

- **Keep the vulnerability private** until we have assessed and fixed it  
- Avoid exploiting the vulnerability beyond what is necessary for reporting  
- Refrain from data extraction, privilege escalation, or destructive testing  
- Avoid automated attacks or denial‑of‑service testing  
- Allow us reasonable time to address the issue (depending on severity)

We commit to:

- Treating your report confidentially  
- Crediting you in release notes if you wish  

---

## 🧪 Security‑Relevant Areas of the Project

The **DMO‑LogicChecker** processes configuration logic and validation rules.  
Particularly sensitive components include:

- Handling of external input (e.g., JSON or YAML structures)  
- Logic for rule validation and interpretation  
- Parser and evaluation functions  
- Modules used in automated pipelines or CI/CD environments  

---

## 🔐 Security Best Practices for Contributors

If you contribute to this project, please follow these guidelines:

- Do not commit sensitive data  
- Avoid including debug information or secrets in the code  
- Use secure libraries and keep dependencies up to date  
- Perform code reviews with a focus on input validation and error handling  
- Do not introduce new dependencies without evaluating their security posture  

---

## 🤝 Thank You

Security is a shared responsibility.  
Thank you for helping make the **DMO‑LogicChecker** more secure.
