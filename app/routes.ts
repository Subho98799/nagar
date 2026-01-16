import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("city-overview", "routes/city-overview.tsx"),
  route("map", "routes/map.tsx"),
  route("report", "routes/report.tsx"),
  route("issue/:id", "routes/issue.$id.tsx"),
  route("admin", "routes/admin.tsx"),
  route("updates", "routes/updates.tsx"),
  route("login", "routes/login.tsx"),
  route("verify-otp", "routes/verify-otp.tsx"),
  route("timeline", "routes/timeline.tsx"),
] satisfies RouteConfig;
