# django-stratagem

Many Django projects reach a point where you want to make the system **configurable** and need a some of the app's behavior to be **swappable**. For instance, if you need to support multiple payment processors and each merchant picks one. Maybe you offer several export formats and users choose CSV, XLSX, or PDF at download time. Maybe different customers get different notification channels depending on their plan.

The usual approach is a mess of nested `if/elif` chains, settings flags, or one-off plugin systems that each work a little differently. django-stratagem replaces all of those with a single pattern: you write each option as a small Python class, and the library auto-discovers it at startup, wires up model fields, populates form and admin dropdowns, and optionally exposes it through DRF.

**How it helps the developer:**

- Add a new option by creating one class in one file. No manual wiring, no migrations.
- Store a user's or tenant's selection in the database with a model field that understands your registry.
- Get dropdowns in forms and the admin automatically - choices stay in sync as you add or remove options.
- Control which options are available to which users using permissions, feature flags, or custom rules.
- Third-party packages can contribute their own options through a plugin entry point.

**What this gives your end users:**

- Admins see a clean dropdown of available options instead of typing class paths or magic strings.
- Options can be enabled, disabled, or restricted per user, role, or tenant without code changes.
- Deploying a new class is enough - no migration needed.

## Example use cases

- **Notification channels** - email, SMS, push, Slack, webhook - let admins pick which channels are active. ([Getting started](quickstart.md))
- **Payment gateways** - Stripe, PayPal, Braintree - store the chosen gateway per merchant in a model field and swap it at runtime.
- **Export/import formats** - CSV, Excel, PDF, JSON - register each format as an option, then offer them as choices in a [form](howto-forms-admin.md) or API endpoint.
- **Authentication backends** - LDAP, SAML, OAuth providers - enable or disable per-tenant with [conditional availability](howto-conditions.md) tied to feature flags or permissions.
- **Pricing / discount strategies** - percentage off, fixed amount, buy-one-get-one - attach the active strategy to a model and let business users pick it in the admin.
- **Report generators** - sales summary, inventory audit, user activity - each report type is a class, and adding a new report is just adding a new module.

```{toctree}
:maxdepth: 2
:caption: Tutorials

quickstart
tutorial
tutorial-construction
```

```{toctree}
:maxdepth: 2
:caption: How-To Guides

howto-fields
howto-forms-admin
howto-templates
howto-conditions
howto-hierarchies
howto-drf
howto-plugins
```

```{toctree}
:maxdepth: 2
:caption: Understand

explanation
hooks
```

```{toctree}
:maxdepth: 2
:caption: Reference

api
contributing
```
