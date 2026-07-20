import { createContext, useContext, useState, type ReactNode } from 'react'

export const ROLES = ['Underwriter', 'Assessor', 'Manager', 'Exec', 'Investigator', 'Admin'] as const
export type Role = (typeof ROLES)[number]

interface RoleCtx {
  role: Role
  setRole: (r: Role) => void
}

const Ctx = createContext<RoleCtx>({ role: 'Assessor', setRole: () => {} })

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>('Assessor')
  return <Ctx.Provider value={{ role, setRole }}>{children}</Ctx.Provider>
}

export function useRole() {
  return useContext(Ctx)
}
