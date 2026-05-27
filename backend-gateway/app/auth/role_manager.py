class Role:
  ADMIN = "ADMIN"
  CLIENT = "CLIENT"
  OPERATIONS = "OPERATIONS"
  AUDITOR = "AUDITOR"
  
  # Backward compatibility aliases
  OPERATOR = "OPERATIONS"
  SECURITY_ANALYST = "AUDITOR"
  CUSTOMER_SUPPORT = "OPERATIONS"

# Map of roles to check inheritance or permissions
ROLE_HIERARCHY = {
  Role.ADMIN: [Role.ADMIN, Role.OPERATIONS, Role.CLIENT, Role.AUDITOR],
  Role.OPERATIONS: [Role.OPERATIONS, Role.CLIENT],
  Role.CLIENT: [Role.CLIENT],
  Role.AUDITOR: [Role.AUDITOR]
}
