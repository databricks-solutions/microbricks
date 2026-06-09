import {
  LayoutDashboard,
  Users,
  CalendarDays,
  Stethoscope,
  Receipt,
  FlaskConical,
  Bell,
} from "lucide-react";
import { Link, useRouterState } from "@tanstack/react-router";

import { Logo } from "@/components/apx/logo";
import { ModeToggle } from "@/components/apx/mode-toggle";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const NAV_ITEMS = [
  { title: "Dashboard", icon: LayoutDashboard, href: "/" },
  { title: "Patients", icon: Users, href: "/patients" },
  { title: "Appointments", icon: CalendarDays, href: "/appointments" },
  { title: "Providers", icon: Stethoscope, href: "/providers" },
  { title: "Billing", icon: Receipt, href: "/billing" },
  { title: "Labs", icon: FlaskConical, href: "/labs" },
  { title: "Alerts", icon: Bell, href: "/alerts" },
];

export function AppSidebar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Logo to="/" />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? currentPath === "/"
                    : currentPath.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild isActive={isActive}>
                      <Link to={item.href}>
                        <item.icon />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-4">
        <ModeToggle />
      </SidebarFooter>
    </Sidebar>
  );
}
