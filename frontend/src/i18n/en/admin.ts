export default {
  nav: {
    users: 'Users'
  },
  users: {
    page: {
      title: 'User management',
      subtitle: 'Create and maintain accounts for your department or the whole platform'
    },
    tabs: {
      users: 'Accounts',
      audit: 'Auth audit'
    },
    table: {
      title: 'Accounts',
      username: 'Username',
      email: 'Email',
      role: 'Role',
      dept: 'Department',
      active: 'Status',
      lock: 'Lock',
      actions: 'Actions',
      empty: 'No users yet'
    },
    role: {
      super_admin: 'Super admin',
      admin: 'Admin',
      user: 'User'
    },
    status: {
      active: 'Active',
      inactive: 'Inactive',
      locked: 'Locked'
    },
    actions: {
      create: 'New user',
      createDept: 'New department',
      save: 'Save',
      deactivate: 'Deactivate',
      activate: 'Activate',
      resetPassword: 'Reset password',
      unlock: 'Unlock',
      delete: 'Delete',
      deleteDisabled: 'At least one super admin must remain'
    },
    audit: {
      title: 'Audit log',
      time: 'Time',
      event: 'Event',
      username: 'Username',
      ip: 'IP',
      detail: 'Detail',
      empty: 'No audit entries yet',
      details: {
        separator: ', ',
        account_locked: 'Account locked',
        account_inactive: 'Account not active',
        pending_approval: 'Awaiting administrator approval',
        roleAssigned: 'Role: {role}',
        fields: {
          is_active: 'Active status',
          email: 'Email',
          role: 'Role',
          dept_id: 'Department',
          password: 'Password'
        }
      },
      events: {
        login_success: 'Login success',
        login_failed: 'Login failed',
        login_locked: 'Login locked',
        login_inactive: 'Sign-in by inactive account',
        logout: 'Logout',
        user_registered: 'Self-registered',
        password_changed: 'Password changed',
        user_created: 'User created',
        user_updated: 'User updated',
        user_deleted: 'User deleted',
        account_unlocked: 'Manual unlock'
      }
    },
    dept: {
      defaultName: 'Default department'
    },
    form: {
      createTitle: 'New account',
      createHint:
        "Fields marked * are required. Username: 3–64 chars (letters, digits, CJK, . _ - {'@'}). Password: 8–128 chars with a letter, digit, and symbol.",
      deptCreateTitle: 'New department',
      deptCreateHint: 'Use a short code identifier; changing codes later can break integrations.',
      username: 'Username',
      password: 'Initial password',
      email: 'Email',
      role: 'Role',
      dept: 'Department',
      deptCode: 'Department code',
      deptName: 'Department name',
      deptOption: '{name} ({code})'
    },
    hint: {
      authOff: 'AUTH_REQUIRE_AUTH is off; user management API is disabled',
      adminScope: 'Admins can only manage regular users in their department',
      pendingApproval: 'Self-registered accounts start as inactive. Verify the person, then click Enable to let them sign in.'
    },
    delete: {
      title: 'Delete account',
      message: 'Delete “{username}”? They will no longer be able to sign in. Cases, requirements, and chat history they created are kept.'
    }
  }
};
