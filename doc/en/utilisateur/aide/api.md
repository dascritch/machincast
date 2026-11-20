# Help on the API tab

![The API tab, its elements numbered as below](../../../fr/captures/aide/api.png)

The API tab manages the accounts that can connect to the intranet and to the API ([#537](https://github.com/dascritch/machincast/issues/537)).
The numbers refer to the picture; **Help → Contextual help**, or <kbd>F1</kbd>, gives each of these helps as a tooltip, on the element itself.

1. **Accounts** (`users`) : each account, its role, its state, `active` or `disabled`, and its creation date; the actions that follow act on the chosen account.
2. **➕ New user…** (`new_user`) : asks for a name, a password of at least 12 characters, its confirmation and a role; the name only takes letters without accents, digits, dot, hyphen and underscore.
3. **Role** (`role`) : `consult` gives the intranet and the API in reading; `API actions` the same, and the actions to come; the change applies at once.
4. **Change the password…** (`change_password`) : a new password, confirmed; the old one is not asked, and there is no other recovery.
5. **Disable** (`disable`) : the account no longer connects; the button becomes **Enable**.
6. **❌ Delete…** (`delete`) : deletes the account, after confirmation.

To go further: [Rights of each program in the database](../../administration/configuration.md#rights-of-each-program-in-the-database).
