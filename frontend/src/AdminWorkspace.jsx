import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
} from "react-leaflet";

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  "https://smart-student-bus-tracker-backend.onrender.com"
).replace(/\/+$/, "");

async function adminRequest(path, token, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.message || `Request failed (${response.status})`
    );
  }

  return data;
}

function readSavedUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "{}");
  } catch {
    return {};
  }
}

const PAGE_META = {
  buses: {
    eyebrow: "FLEET OPERATIONS",
    title: "Bus management",
    description:
      "Register buses, assign each bus a route and driver, and monitor the fleet.",
    icon: "🚌",
  },

  drivers: {
    eyebrow: "PEOPLE & ASSIGNMENTS",
    title: "Driver management",
    description:
      "Create driver accounts and review current bus assignments.",
    icon: "👨‍✈️",
  },

  parents: {
    eyebrow: "FAMILY ACCOUNTS",
    title: "Parent management",
    description:
      "Review family accounts and the children linked to each account.",
    icon: "👨‍👩‍👧",
  },

  "live-bus-location": {
    eyebrow: "LIVE OPERATIONS",
    title: "Live bus tracking",
    description:
      "Monitor the latest reported bus position and current tracking status.",
    icon: "📍",
  },

  attendance: {
    eyebrow: "STUDENT SAFETY",
    title: "Attendance records",
    description:
      "Review recorded pickup and drop attendance for a selected date.",
    icon: "📊",
  },

  notifications: {
    eyebrow: "COMMUNICATION CENTRE",
    title: "Notifications",
    description:
      "Review notification events recorded for parent accounts.",
    icon: "🔔",
  },

  announcements: {
    eyebrow: "COMMUNICATION CENTRE",
    title: "Announcements",
    description:
      "Publish a message for linked families and keep a record of notices.",
    icon: "📢",
  },

  settings: {
    eyebrow: "SYSTEM PREFERENCES",
    title: "Settings",
    description:
      "Manage display preferences for this browser.",
    icon: "⚙️",
  },

  "my-profile": {
    eyebrow: "ACCOUNT",
    title: "Admin profile",
    description:
      "Review the account currently signed in to the administration panel.",
    icon: "👤",
  },
};

function Notice({ kind = "info", children }) {
  if (!children) return null;

  return (
    <div
      className={`adm-notice adm-notice-${kind}`}
      role="status"
    >
      {children}
    </div>
  );
}

function EmptyState({ title, detail }) {
  return (
    <div className="adm-empty-state">
      <span className="adm-empty-icon">⌕</span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function Table({
  headers,
  children,
  emptyTitle,
  emptyDetail,
  isEmpty,
}) {
  if (isEmpty) {
    return (
      <EmptyState
        title={emptyTitle || "No records yet"}
        detail={
          emptyDetail ||
          "Records will appear here when available."
        }
      />
    );
  }

  return (
    <div className="adm-table-scroll">
      <table className="adm-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>

        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function StatusChip({
  children,
  variant = "neutral",
}) {
  return (
    <span className={`adm-status-chip adm-status-${variant}`}>
      {children}
    </span>
  );
}

export default function AdminWorkspace({
  selectedMenu,
  token,
  busLocation,
  busLocationStatus,
}) {
  const page = PAGE_META[selectedMenu];

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [buses, setBuses] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [parents, setParents] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [announcements, setAnnouncements] = useState([]);

  const [profile, setProfile] = useState(readSavedUser);

  const [query, setQuery] = useState("");
  const [reloadVersion, setReloadVersion] = useState(0);

  const [attendanceDate, setAttendanceDate] = useState(() => {
    const now = new Date();

    return `${now.getFullYear()}-${String(
      now.getMonth() + 1
    ).padStart(2, "0")}-${String(now.getDate()).padStart(
      2,
      "0"
    )}`;
  });

  const [settings, setSettings] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem("smart-bus-admin-preferences") ||
          "{}"
      );
    } catch {
      return {};
    }
  });

  const [busFormOpen, setBusFormOpen] = useState(false);
  const [driverFormOpen, setDriverFormOpen] = useState(false);
  const [parentFormOpen, setParentFormOpen] = useState(false);
  const [announcementFormOpen, setAnnouncementFormOpen] =
    useState(false);

  const [selectedBusId, setSelectedBusId] = useState("");

  const [busLocationDetails, setBusLocationDetails] =
    useState(busLocation || null);

  // LOAD DATA FOR THE SELECTED ADMIN PAGE

  useEffect(() => {
    setError("");
    setNotice("");
    setQuery("");

    if (!page) return;

    let cancelled = false;

    const load = async () => {
      setLoading(true);

      try {
        switch (selectedMenu) {
          case "buses": {
            const [busData, driverData, routeData] = await Promise.all([
              adminRequest("/api/admin/buses", token),
              adminRequest("/api/admin/drivers", token),
              adminRequest("/api/admin/routes", token),
            ]);

            if (cancelled) return;

            setBuses(busData.buses || []);
            setDrivers(driverData.drivers || []);
            setRoutes(routeData.routes || []);

            break;
          }

          case "drivers": {
            const data = await adminRequest(
              "/api/admin/drivers",
              token
            );

            if (!cancelled) {
              setDrivers(data.drivers || []);
            }

            break;
          }

          case "parents": {
            const data = await adminRequest(
              "/api/admin/parents",
              token
            );

            if (!cancelled) {
              setParents(data.parents || []);
            }

            break;
          }

          case "live-bus-location": {
            const data = await adminRequest(
              "/api/admin/buses",
              token
            );

            if (cancelled) return;

            const list = data.buses || [];

            setBuses(list);

            const preferred =
              list.find((bus) => String(bus.id) === String(selectedBusId)) ||
              list[0];

            if (preferred) {
              setSelectedBusId(String(preferred.id));
              setBusLocationDetails(preferred);
            } else if (!cancelled) {
              setSelectedBusId("");
              setBusLocationDetails(null);
            }

            break;
          }

          case "attendance": {
            const data = await adminRequest(
              `/api/admin/attendance?date=${encodeURIComponent(
                attendanceDate
              )}`,
              token
            );

            if (!cancelled) {
              setAttendance(data.attendance || []);
            }

            break;
          }

          case "notifications": {
            const data = await adminRequest(
              "/api/admin/notifications",
              token
            );

            if (!cancelled) {
              setNotifications(data.notifications || []);
            }

            break;
          }

          case "announcements": {
            const data = await adminRequest(
              "/api/admin/announcements",
              token
            );

            if (!cancelled) {
              setAnnouncements(data.announcements || []);
            }

            break;
          }

          case "my-profile": {
            try {
              const data = await adminRequest(
                "/api/admin/profile",
                token
              );

              if (!cancelled) {
                setProfile(data.profile || readSavedUser());
              }
            } catch {
              if (!cancelled) {
                setProfile(readSavedUser());
              }
            }

            break;
          }

          case "settings":
            break;

          default:
            break;
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            requestError.message ||
              "Could not load this section."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [
    selectedMenu,
    token,
    reloadVersion,
    attendanceDate,
  ]);

  // KEEP THE SHARED BUS LOCATION UPDATED

  useEffect(() => {
    if (busLocation) setBusLocationDetails(busLocation);
  }, [busLocation]);

  // REFRESH ALL ACTIVE BUS LOCATIONS EVERY 10 SECONDS
  // The Admin map receives one live coordinate set per bus.
  useEffect(() => {
    if (selectedMenu !== "live-bus-location" || !token) {
      return;
    }

    let cancelled = false;

    const refreshFleet = async () => {
      try {
        const data = await adminRequest("/api/admin/buses", token);
        if (cancelled) return;

        const list = data.buses || [];
        setBuses(list);

        const selected =
          list.find((bus) => String(bus.id) === String(selectedBusId)) ||
          list[0] || null;

        if (selected) {
          setSelectedBusId(String(selected.id));
          setBusLocationDetails(selected);
        } else {
          setBusLocationDetails(null);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError.message || "Unable to refresh fleet locations.");
        }
      }
    };

    refreshFleet();
    const timer = window.setInterval(refreshFleet, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedMenu, selectedBusId, token]);

  // SEARCH FILTERS

  const matchingBuses = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return buses;

    return buses.filter((bus) =>
      [
        bus.bus_number,
        bus.registration_number,
        bus.driver_name,
        bus.route_name,
        bus.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [buses, query]);

  const matchingDrivers = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return drivers;

    return drivers.filter((driver) =>
      [
        driver.name,
        driver.username,
        driver.phone,
        driver.license_number,
        driver.bus_number,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [drivers, query]);

  const matchingParents = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return parents;

    return parents.filter((parent) =>
      [
        parent.name,
        parent.username,
        parent.father_name,
        parent.mother_name,
        parent.email,
        parent.phone,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [parents, query]);

  const matchingAttendance = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return attendance;

    return attendance.filter((record) =>
      [
        record.student_name,
        record.student_code,
        record.class_name,
        record.bus_number,
        record.driver_name,
        record.status,
        record.attendance_type,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [attendance, query]);

  const matchingNotifications = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return notifications;

    return notifications.filter((item) =>
      [
        item.title,
        item.message,
        item.parent_name,
        item.student_name,
        item.type,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [notifications, query]);

  const matchingAnnouncements = useMemo(() => {
    const text = query.trim().toLowerCase();

    if (!text) return announcements;

    return announcements.filter((item) =>
      [
        item.title,
        item.description,
        item.message,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(text)
    );
  }, [announcements, query]);

  // COMMON FORM SUBMISSION

  const submitWithForm = async (
    event,
    endpoint,
    onSuccess,
    transform
  ) => {
    event.preventDefault();

    setError("");
    setNotice("");

    const form = event.currentTarget;
    const formData = new FormData(form);
    const values = Object.fromEntries(formData.entries());

    const payload = transform
      ? transform(values)
      : values;

    try {
      const data = await adminRequest(endpoint, token, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setNotice(data.message || "Saved successfully.");

      form.reset();

      onSuccess?.(data);

      setReloadVersion((value) => value + 1);
    } catch (requestError) {
      setError(
        requestError.message ||
          "Unable to save this record."
      );
    }
  };

  // ASSIGN DRIVER TO BUS

  const assignDriver = async (event, busId) => {
    event.preventDefault();

    setError("");
    setNotice("");

    const driverId = new FormData(
      event.currentTarget
    ).get("driver_id");

    if (!driverId) {
      setError("Select a driver before assigning the bus.");
      return;
    }

    try {
      const data = await adminRequest(
        `/api/buses/${busId}/assign-driver`,
        token,
        {
          method: "POST",
          body: JSON.stringify({
            driver_id: Number(driverId),
          }),
        }
      );

      setNotice(
        data.message || "Driver assignment saved."
      );

      setReloadVersion((value) => value + 1);
    } catch (requestError) {
      setError(
        requestError.message ||
          "Unable to assign this driver."
      );
    }
  };

  // ASSIGN ROUTE TO BUS
  const assignRoute = async (event, busId) => {
    event.preventDefault();
    setError("");
    setNotice("");

    const routeId = new FormData(event.currentTarget).get("route_id");
    if (!routeId) {
      setError("Select a route before assigning the bus.");
      return;
    }

    try {
      await adminRequest(`/api/buses/${busId}`, token, {
        method: "PATCH",
        body: JSON.stringify({ route_id: Number(routeId) }),
      });
      setNotice("Route assigned to bus successfully.");
      setReloadVersion((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message || "Unable to assign this route.");
    }
  };

  // SAVE ADMIN DISPLAY PREFERENCES

  const saveSettings = (next) => {
    setSettings(next);

    localStorage.setItem(
      "smart-bus-admin-preferences",
      JSON.stringify(next)
    );

    setNotice("Preferences saved in this browser.");
  };

  if (!page) return null;

  const mapLocation =
    busLocationDetails &&
    Number.isFinite(Number(busLocationDetails.latitude)) &&
    Number.isFinite(Number(busLocationDetails.longitude))
      ? [
          Number(busLocationDetails.latitude),
          Number(busLocationDetails.longitude),
        ]
      : [17.289612892928957, 76.86886054620065];

  return (
    <section
      className={`admin-module-page${
        settings.compactTables
          ? " adm-compact-tables"
          : ""
      }${
        settings.reduceMotion
          ? " adm-reduced-motion"
          : ""
      }`}
    >
      {/* PAGE HEADER */}

      <div className="admin-module-header">
        <div className="admin-module-heading-copy">
          <p className="admin-module-eyebrow">
            {page.eyebrow}
          </p>

          <h2>
            <span className="admin-module-title-icon">
              {page.icon}
            </span>
            {page.title}
          </h2>

          <p>{page.description}</p>
        </div>

        <div className="admin-module-header-actions">
          {[
            "buses",
            "drivers",
            "parents",
            "announcements",
          ].includes(selectedMenu) && (
            <button
              type="button"
              className="adm-button adm-button-primary"
              onClick={() => {
                setBusFormOpen(
                  selectedMenu === "buses"
                    ? !busFormOpen
                    : false
                );

                setDriverFormOpen(
                  selectedMenu === "drivers"
                    ? !driverFormOpen
                    : false
                );

                setParentFormOpen(
                  selectedMenu === "parents"
                    ? !parentFormOpen
                    : false
                );

                setAnnouncementFormOpen(
                  selectedMenu === "announcements"
                    ? !announcementFormOpen
                    : false
                );

                setError("");
                setNotice("");
              }}
            >
              {(
                (selectedMenu === "buses" && busFormOpen) ||
                (selectedMenu === "drivers" && driverFormOpen) ||
                (selectedMenu === "parents" && parentFormOpen) ||
                (
                  selectedMenu === "announcements" &&
                  announcementFormOpen
                )
              )
                ? "Close form"
                : selectedMenu === "buses"
                  ? "+ Add Bus"
                  : selectedMenu === "drivers"
                    ? "+ Add Driver"
                    : selectedMenu === "parents"
                      ? "+ Add Parent"
                      : "+ New Announcement"}
            </button>
          )}

          <button
            type="button"
            className="adm-button adm-button-secondary"
            onClick={() =>
              setReloadVersion((value) => value + 1)
            }
            disabled={loading}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      <Notice kind="success">{notice}</Notice>
      <Notice kind="error">{error}</Notice>

      {loading && (
        <div className="adm-loading">
          <span className="adm-spinner" />
          Loading {page.title.toLowerCase()}…
        </div>
      )}

      {/* BUS MANAGEMENT */}

      {selectedMenu === "buses" && (
        <>
          {busFormOpen && (
            <form
              className="adm-card adm-form-card"
              onSubmit={(event) =>
                submitWithForm(
                  event,
                  "/api/buses",
                  () => setBusFormOpen(false)
                )
              }
            >
              <div className="adm-card-heading">
                <div>
                  <h3>Add bus</h3>
                  <p>
                    Register a vehicle in the transport network.
                  </p>
                </div>
              </div>

              <div className="adm-form-grid">
                <label>
                  Bus number
                  <input
                    name="bus_number"
                    required
                    placeholder="BUS002"
                  />
                </label>

                <label>
                  Registration number
                  <input
                    name="registration_number"
                    placeholder="KA-32-AB-1234"
                  />
                </label>

                <label>
                  Capacity
                  <input
                    name="capacity"
                    type="number"
                    min="1"
                    placeholder="40"
                  />
                </label>

                <label>
                  Status
                  <select name="status" defaultValue="ACTIVE">
                    <option value="ACTIVE">Active</option>
                    <option value="MAINTENANCE">
                      Maintenance
                    </option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </label>
              </div>

              <div className="adm-form-actions">
                <button
                  className="adm-button adm-button-primary"
                  type="submit"
                >
                  Save bus
                </button>

                <button
                  className="adm-button adm-button-secondary"
                  type="button"
                  onClick={() => setBusFormOpen(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="adm-metric-row">
            <div className="adm-metric-card">
              <span>Registered buses</span>
              <strong>{buses.length}</strong>
              <small>
                Active vehicle records returned by the server
              </small>
            </div>

            <div className="adm-metric-card">
              <span>Assigned drivers</span>
              <strong>
                {buses.filter((bus) => bus.driver_id).length}
              </strong>
              <small>
                Vehicles with an active driver assignment
              </small>
            </div>

            <div className="adm-metric-card">
              <span>Available drivers</span>
              <strong>{drivers.length}</strong>
              <small>
                Driver profiles available for assignment
              </small>
            </div>
          </div>

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Fleet register</h3>
                <p>
                  Search vehicle numbers, registration plates or
                  assigned drivers.
                </p>
              </div>

              <input
                className="adm-search-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                placeholder="Search buses…"
              />
            </div>

            <Table
              headers={[
                "BUS",
                "REGISTRATION",
                "CAPACITY",
                "DRIVER",
                "ROUTE",
                "STATUS",
                "ASSIGN DRIVER",
                "ASSIGN ROUTE",
              ]}
              isEmpty={!matchingBuses.length && !loading}
              emptyTitle="No bus records found"
              emptyDetail="Create the first bus record using Add Bus."
            >
              {matchingBuses.map((bus) => (
                <tr key={bus.id}>
                  <td>
                    <strong>
                      {bus.bus_number || `BUS ${bus.id}`}
                    </strong>
                    <small className="adm-subcell">
                      ID {bus.id}
                    </small>
                  </td>

                  <td>
                    {bus.registration_number || "Not entered"}
                  </td>

                  <td>{bus.capacity ?? "—"}</td>

                  <td>
                    {bus.driver_id && bus.driver_name ? (
                      <>
                        <strong>{bus.driver_name}</strong>
                        <small className="adm-subcell">
                          <StatusChip variant="success">ASSIGNED</StatusChip>
                        </small>
                      </>
                    ) : (
                      <>
                        <strong>Not assigned</strong>
                        <small className="adm-subcell">
                          <StatusChip variant="neutral">PENDING</StatusChip>
                        </small>
                      </>
                    )}
                  </td>
                  <td>
                    {bus.route_id && bus.route_name ? (
                      <>
                        <strong>{bus.route_name}</strong>
                        <small className="adm-subcell">
                          <StatusChip variant="success">ASSIGNED</StatusChip>
                        </small>
                      </>
                    ) : (
                      <>
                        <strong>Not assigned</strong>
                        <small className="adm-subcell">
                          <StatusChip variant="neutral">PENDING</StatusChip>
                        </small>
                      </>
                    )}
                  </td>

                  <td>
                    <StatusChip
                      variant={
                        String(bus.status).toLowerCase() ===
                        "active"
                          ? "success"
                          : "neutral"
                      }
                    >
                      {bus.status || "UNKNOWN"}
                    </StatusChip>
                  </td>

                  <td>
                    <form
                      className="adm-inline-assign"
                      onSubmit={(event) =>
                        assignDriver(event, bus.id)
                      }
                    >
                      <select
                        aria-label={`Choose driver for ${bus.bus_number}`}
                        key={`driver-${bus.id}-${bus.driver_id || "none"}-${reloadVersion}`}
                        name="driver_id"
                        defaultValue={bus.driver_id || ""}
                      >
                        <option value="">Choose driver</option>

                        {drivers.map((driver) => (
                          <option
                            key={driver.id}
                            value={driver.id}
                          >
                            {driver.name} · ID {driver.id}
                          </option>
                        ))}
                      </select>

                      <button
                        type="submit"
                        className="adm-button adm-button-small"
                      >
                        Assign
                      </button>
                    </form>
                  </td>

                  <td>
                    <form
                      className="adm-inline-assign"
                      onSubmit={(event) => assignRoute(event, bus.id)}
                    >
                      <select
                        aria-label={`Choose route for ${bus.bus_number}`}
                        key={`route-${bus.id}-${bus.route_id || "none"}-${reloadVersion}`}
                        name="route_id"
                        defaultValue={bus.route_id || ""}
                        disabled={routes.length === 0}
                      >
                        <option value="">Choose route</option>
                        {routes.map((route) => (
                          <option key={route.id} value={route.id}>
                            {route.route_name}
                          </option>
                        ))}
                      </select>
                      <button
                        type="submit"
                        className="adm-button adm-button-small"
                        disabled={routes.length === 0}
                      >
                        Assign
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}

      {/* DRIVER MANAGEMENT */}

      {selectedMenu === "drivers" && (
        <>
          {driverFormOpen && (
            <form
              className="adm-card adm-form-card"
              onSubmit={(event) =>
                submitWithForm(
                  event,
                  "/api/drivers",
                  () => setDriverFormOpen(false)
                )
              }
            >
              <div className="adm-card-heading">
                <div>
                  <h3>Create driver account</h3>
                  <p>
                    Driver username and password are used to sign
                    in to the Driver interface.
                  </p>
                </div>
              </div>

              <div className="adm-form-grid">
                <label>
                  Driver full name
                  <input
                    name="name"
                    required
                    placeholder="Enter driver name"
                  />
                </label>

                <label>
                  Username
                  <input
                    name="username"
                    required
                    placeholder="driver001"
                  />
                </label>

                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    required
                    minLength="8"
                    placeholder="Create a strong password"
                  />
                </label>

                <label>
                  Phone
                  <input name="phone" placeholder="Optional" />
                </label>

                <label>
                  License number
                  <input
                    name="license_number"
                    placeholder="Optional"
                  />
                </label>
              </div>

              <div className="adm-form-actions">
                <button
                  className="adm-button adm-button-primary"
                  type="submit"
                >
                  Create driver
                </button>

                <button
                  className="adm-button adm-button-secondary"
                  type="button"
                  onClick={() => setDriverFormOpen(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Driver directory</h3>
                <p>
                  Driver accounts and current bus assignments.
                </p>
              </div>

              <input
                className="adm-search-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                placeholder="Search drivers…"
              />
            </div>

            <Table
              headers={[
                "DRIVER",
                "USERNAME",
                "PHONE",
                "LICENSE",
                "ASSIGNED BUS",
                "ACCOUNT",
              ]}
              isEmpty={!matchingDrivers.length && !loading}
              emptyTitle="No driver records found"
              emptyDetail="Use Add Driver to create the first driver account."
            >
              {matchingDrivers.map((driver) => (
                <tr key={driver.id}>
                  <td>
                    <strong>{driver.name}</strong>
                    <small className="adm-subcell">
                      Driver ID {driver.id}
                    </small>
                  </td>

                  <td>{driver.username || "—"}</td>
                  <td>{driver.phone || "—"}</td>
                  <td>{driver.license_number || "—"}</td>
                  <td>{driver.bus_number || "Not assigned"}</td>

                  <td>
                    <StatusChip
                      variant={
                        Number(driver.account_active) === 0
                          ? "danger"
                          : "success"
                      }
                    >
                      {Number(driver.account_active) === 0
                        ? "INACTIVE"
                        : "ACTIVE"}
                    </StatusChip>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}

      {/* PARENT MANAGEMENT */}

      {selectedMenu === "parents" && (
        <>
          {parentFormOpen && (
            <form
              className="adm-card adm-form-card"
              onSubmit={(event) =>
                submitWithForm(
                  event,
                  "/api/parents",
                  () => setParentFormOpen(false)
                )
              }
            >
              <div className="adm-card-heading">
                <div>
                  <h3>Create parent account</h3>
                  <p>
                    For a student-linked family account, use
                    Students → Add Student and enter the family
                    details there.
                  </p>
                </div>
              </div>

              <div className="adm-form-grid">
                <label>
                  Family display name
                  <input
                    name="name"
                    required
                    placeholder="Parent or family name"
                  />
                </label>

                <label>
                  Parent username
                  <input
                    name="username"
                    required
                    placeholder="parent00003"
                  />
                </label>

                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    minLength="8"
                    required
                    placeholder="Create a strong password"
                  />
                </label>

                <label>
                  Phone
                  <input name="phone" placeholder="Optional" />
                </label>

                <label>
                  Email
                  <input
                    name="email"
                    type="email"
                    placeholder="Optional"
                  />
                </label>
              </div>

              <div className="adm-form-actions">
                <button
                  className="adm-button adm-button-primary"
                  type="submit"
                >
                  Create parent
                </button>

                <button
                  className="adm-button adm-button-secondary"
                  type="button"
                  onClick={() => setParentFormOpen(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="adm-metric-row">
            <div className="adm-metric-card">
              <span>Parent accounts</span>
              <strong>{parents.length}</strong>
              <small>Family accounts in the database</small>
            </div>

            <div className="adm-metric-card">
              <span>Linked children</span>
              <strong>
                {parents.reduce(
                  (total, parent) =>
                    total + Number(parent.child_count || 0),
                  0
                )}
              </strong>
              <small>
                Total parent–student links counted by the server
              </small>
            </div>

            <div className="adm-metric-card">
              <span>Accounts without children</span>
              <strong>
                {
                  parents.filter(
                    (parent) =>
                      Number(parent.child_count || 0) === 0
                  ).length
                }
              </strong>
              <small>
                Review these accounts if they should be linked
              </small>
            </div>
          </div>

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Family directory</h3>
                <p>
                  Parent accounts and linked student count.
                </p>
              </div>

              <input
                className="adm-search-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                placeholder="Search parents…"
              />
            </div>

            <Table
              headers={[
                "FAMILY",
                "USERNAME",
                "PHONE",
                "EMAIL",
                "CHILDREN",
                "ACCOUNT",
              ]}
              isEmpty={!matchingParents.length && !loading}
              emptyTitle="No parent records found"
              emptyDetail="Parent accounts appear here once they are created in the system."
            >
              {matchingParents.map((parent) => (
                <tr key={parent.id}>
                  <td>
                    <strong>
                      {parent.name ||
                        [
                          parent.father_name,
                          parent.mother_name,
                        ]
                          .filter(Boolean)
                          .join(" & ") ||
                        "Family"}
                    </strong>

                    <small className="adm-subcell">
                      Parent ID {parent.id}
                    </small>
                  </td>

                  <td>{parent.username || "—"}</td>
                  <td>{parent.phone || "—"}</td>
                  <td>{parent.email || "—"}</td>
                  <td>{Number(parent.child_count || 0)}</td>

                  <td>
                    <StatusChip
                      variant={
                        Number(parent.account_active) === 0
                          ? "danger"
                          : "success"
                      }
                    >
                      {Number(parent.account_active) === 0
                        ? "INACTIVE"
                        : "ACTIVE"}
                    </StatusChip>
                  </td>
                </tr>
              ))}
            </Table>
          </div>
        </>
      )}

      {/* LIVE BUS TRACKING */}

      {selectedMenu === "live-bus-location" && (
        <>
          <div className="adm-metric-row">
            <div className="adm-metric-card">
              <span>Tracking status</span>
              <strong>
                {buses.filter((bus) => bus.latitude != null && bus.longitude != null).length} / {buses.length}
              </strong>
              <small>Active buses with a latest GPS point</small>
            </div>

            <div className="adm-metric-card">
              <span>Latitude</span>
              <strong>
                {busLocationDetails?.latitude != null
                  ? Number(
                      busLocationDetails.latitude
                    ).toFixed(5)
                  : "—"}
              </strong>
              <small>Latest reported coordinate</small>
            </div>

            <div className="adm-metric-card">
              <span>Longitude</span>
              <strong>
                {busLocationDetails?.longitude != null
                  ? Number(
                      busLocationDetails.longitude
                    ).toFixed(5)
                  : "—"}
              </strong>
              <small>Latest reported coordinate</small>
            </div>
          </div>

          <div className="adm-card adm-map-card">
            <div className="adm-card-heading">
              <div>
                <h3>Fleet map</h3>
                <p>
                  Each marker represents a bus with a current active-trip GPS report. Refreshes automatically every 10 seconds.
                </p>
              </div>

              {buses.length > 0 && (
                <label className="adm-map-bus-select">
                  BUS

                  <select
                    value={selectedBusId}
                    onChange={(event) => {
                      const id = event.target.value;
                      setSelectedBusId(id);
                      setError("");
                      setBusLocationDetails(
                        buses.find((bus) => String(bus.id) === String(id)) || null
                      );
                    }}
                  >
                    {buses.map((bus) => (
                      <option key={bus.id} value={bus.id}>
                        {bus.bus_number}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>

            <div className="adm-map-canvas">
              <MapContainer
                center={mapLocation}
                zoom={14}
                scrollWheelZoom
                style={{
                  width: "100%",
                  height: "100%",
                }}
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {buses
                  .filter((bus) =>
                    bus.latitude !== null && bus.latitude !== undefined &&
                    bus.longitude !== null && bus.longitude !== undefined &&
                    Number.isFinite(Number(bus.latitude)) &&
                    Number.isFinite(Number(bus.longitude))
                  )
                  .map((bus) => (
                    <Marker
                      key={bus.id}
                      position={[Number(bus.latitude), Number(bus.longitude)]}
                    >
                      <Popup>
                        <strong>{bus.bus_number || `BUS ${bus.id}`}</strong>
                        <br />Route: {bus.route_name || "Not assigned"}
                        <br />Driver: {bus.driver_name || "Not assigned"}
                        <br />Trip: {bus.active_trip_type || "No active trip"}
                        <br />Last update: {bus.recorded_at || "Not available"}
                      </Popup>
                    </Marker>
                  ))}
              </MapContainer>

              {!buses.some((bus) => bus.latitude != null && bus.longitude != null) && (
                <div className="adm-map-overlay">
                  <strong>Waiting for fleet GPS</strong>
                  <span>Start a trip from a Driver account. Every active bus will appear here after its first GPS update.</span>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ATTENDANCE RECORDS */}

      {selectedMenu === "attendance" && (
        <div className="adm-card">
          <div className="adm-card-heading">
            <div>
              <h3>Attendance register</h3>
              <p>
                Records are loaded for the selected attendance
                date.
              </p>
            </div>

            <div className="adm-filter-row">
              <label>
                DATE
                <input
                  type="date"
                  value={attendanceDate}
                  onChange={(event) =>
                    setAttendanceDate(event.target.value)
                  }
                />
              </label>

              <input
                className="adm-search-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                placeholder="Search attendance…"
              />
            </div>
          </div>

          <div className="adm-metric-row adm-metric-row-compact">
            <div className="adm-metric-card">
              <span>Present</span>
              <strong>
                {
                  matchingAttendance.filter(
                    (item) =>
                      String(item.status).toUpperCase() ===
                      "PRESENT"
                  ).length
                }
              </strong>
            </div>

            <div className="adm-metric-card">
              <span>Absent / Pending</span>
              <strong>
                {
                  matchingAttendance.filter((item) =>
                    ["ABSENT", "PENDING"].includes(
                      String(item.status).toUpperCase()
                    )
                  ).length
                }
              </strong>
            </div>

            <div className="adm-metric-card">
              <span>Total records</span>
              <strong>{matchingAttendance.length}</strong>
            </div>
          </div>

          <Table
            headers={[
              "STUDENT",
              "CLASS",
              "DATE",
              "TYPE",
              "STATUS",
              "BUS / ROUTE",
              "METHOD",
              "TIME",
            ]}
            isEmpty={!matchingAttendance.length && !loading}
            emptyTitle="No attendance for this date"
            emptyDetail="Try another date or review the Driver attendance flow."
          >
            {matchingAttendance.map((record) => (
              <tr key={record.id}>
                <td>
                  <strong>
                    {record.student_name || "Student"}
                  </strong>

                  <small className="adm-subcell">
                    {record.student_code ||
                      `ID ${record.student_id}`}
                  </small>
                </td>

                <td>{record.class_name || "—"}</td>
                <td>{record.attendance_date || "—"}</td>
                <td>{record.attendance_type || "—"}</td>

                <td>
                  <StatusChip
                    variant={
                      String(record.status).toLowerCase() ===
                      "present"
                        ? "success"
                        : String(record.status).toLowerCase() ===
                            "absent"
                          ? "danger"
                          : "neutral"
                    }
                  >
                    {record.status || "—"}
                  </StatusChip>
                </td>

                <td>
                  {[
                    record.bus_number,
                    record.route_name,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </td>

                <td>{record.method || "—"}</td>

                <td>
                  {record.recognized_at ||
                    record.recorded_at ||
                    "—"}
                </td>
              </tr>
            ))}
          </Table>
        </div>
      )}

      {/* NOTIFICATIONS */}

      {selectedMenu === "notifications" && (
        <div className="adm-card">
          <div className="adm-card-heading">
            <div>
              <h3>Notification feed</h3>
              <p>
                Transport notices and attendance-generated parent
                alerts.
              </p>
            </div>

            <input
              className="adm-search-input"
              value={query}
              onChange={(event) =>
                setQuery(event.target.value)
              }
              placeholder="Search notifications…"
            />
          </div>

          {matchingNotifications.length === 0 && !loading ? (
            <EmptyState
              title="No notifications found"
              detail="Notifications will appear here when the system records a parent-facing event."
            />
          ) : (
            <div className="adm-notification-list">
              {matchingNotifications.map((item) => (
                <article
                  className="adm-notification-item"
                  key={item.id}
                >
                  <span className="adm-notification-dot">
                    {item.type === "ANNOUNCEMENT"
                      ? "📢"
                      : "🔔"}
                  </span>

                  <div className="adm-notification-copy">
                    <div className="adm-notification-title-row">
                      <strong>
                        {item.title ||
                          item.type ||
                          "Notification"}
                      </strong>

                      <small>{item.created_at || ""}</small>
                    </div>

                    <p>{item.message}</p>

                    <small>
                      Parent:{" "}
                      {item.parent_name ||
                        item.parent_username ||
                        "—"}{" "}
                      · Student: {item.student_name || "—"} ·{" "}
                      {item.is_read ? "Read" : "Unread"}
                    </small>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ANNOUNCEMENTS */}

      {selectedMenu === "announcements" && (
        <>
          {announcementFormOpen && (
            <form
              className="adm-card adm-form-card"
              onSubmit={(event) =>
                submitWithForm(
                  event,
                  "/api/admin/announcements",
                  () => setAnnouncementFormOpen(false),
                  (values) => ({
                    title: values.title,
                    message: values.message,
                    event_date:
                      values.event_date ||
                      new Date().toISOString(),
                  })
                )
              }
            >
              <div className="adm-card-heading">
                <div>
                  <h3>Publish announcement</h3>
                  <p>
                    The announcement is saved to the event log
                    and sent as a notification to linked families.
                  </p>
                </div>
              </div>

              <div className="adm-form-grid adm-form-grid-one">
                <label>
                  Announcement title
                  <input
                    name="title"
                    required
                    maxLength="120"
                    placeholder="e.g. School bus timing update"
                  />
                </label>

                <label>
                  Message
                  <textarea
                    name="message"
                    required
                    rows="4"
                    maxLength="1500"
                    placeholder="Write the announcement for parents…"
                  />
                </label>

                <label>
                  Publish date / time
                  <input
                    name="event_date"
                    type="datetime-local"
                  />
                </label>
              </div>

              <div className="adm-form-actions">
                <button
                  className="adm-button adm-button-primary"
                  type="submit"
                >
                  Publish announcement
                </button>

                <button
                  className="adm-button adm-button-secondary"
                  type="button"
                  onClick={() =>
                    setAnnouncementFormOpen(false)
                  }
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Announcement history</h3>
                <p>
                  Published notices recorded by Admin.
                </p>
              </div>

              <input
                className="adm-search-input"
                value={query}
                onChange={(event) =>
                  setQuery(event.target.value)
                }
                placeholder="Search announcements…"
              />
            </div>

            {matchingAnnouncements.length === 0 && !loading ? (
              <EmptyState
                title="No announcements yet"
                detail="Select New Announcement to publish the first notice."
              />
            ) : (
              <div className="adm-announcement-list">
                {matchingAnnouncements.map((item) => (
                  <article
                    className="adm-announcement-item"
                    key={item.id}
                  >
                    <div className="adm-announcement-icon">
                      📢
                    </div>

                    <div>
                      <p className="adm-module-eyebrow">
                        {item.event_date ||
                          item.created_at ||
                          "Announcement"}
                      </p>

                      <h3>{item.title}</h3>

                      <p>
                        {item.description ||
                          item.message ||
                          "—"}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* SETTINGS */}

      {selectedMenu === "settings" && (
        <div className="adm-settings-grid">
          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Interface preferences</h3>
                <p>
                  These settings are saved in this browser only;
                  they do not change backend security or data.
                </p>
              </div>
            </div>

            <label className="adm-setting-row">
              <span>
                <strong>Compact tables</strong>
                <small>
                  Use tighter row spacing in Admin data tables.
                </small>
              </span>

              <input
                type="checkbox"
                checked={Boolean(settings.compactTables)}
                onChange={(event) =>
                  saveSettings({
                    ...settings,
                    compactTables: event.target.checked,
                  })
                }
              />
            </label>

            <label className="adm-setting-row">
              <span>
                <strong>Reduce motion</strong>
                <small>
                  Limit small hover and transition effects in
                  this browser.
                </small>
              </span>

              <input
                type="checkbox"
                checked={Boolean(settings.reduceMotion)}
                onChange={(event) =>
                  saveSettings({
                    ...settings,
                    reduceMotion: event.target.checked,
                  })
                }
              />
            </label>

            <div className="adm-form-actions">
              <button
                className="adm-button adm-button-secondary"
                type="button"
                onClick={() => {
                  const defaults = {
                    compactTables: false,
                    reduceMotion: false,
                  };

                  saveSettings(defaults);
                }}
              >
                Reset preferences
              </button>
            </div>
          </div>

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Service information</h3>
                <p>Current application connection.</p>
              </div>
            </div>

            <div className="adm-info-row">
              <span>Frontend</span>
              <strong>React + Vite</strong>
            </div>

            <div className="adm-info-row">
              <span>Backend</span>
              <strong>Flask API</strong>
            </div>

            <div className="adm-info-row">
              <span>API host</span>
              <strong className="adm-break-word">
                {API_BASE}
              </strong>
            </div>

            <div className="adm-info-row">
              <span>Session token</span>

              <StatusChip
                variant={token ? "success" : "danger"}
              >
                {token ? "Available" : "Missing"}
              </StatusChip>
            </div>
          </div>
        </div>
      )}

      {/* ADMIN PROFILE */}

      {selectedMenu === "my-profile" && (
        <div className="adm-profile-grid">
          <div className="adm-profile-card">
            <div className="adm-profile-avatar">
              {String(
                profile.username || profile.name || "A"
              )
                .trim()
                .slice(0, 1)
                .toUpperCase()}
            </div>

            <p className="adm-module-eyebrow">
              SIGNED-IN ACCOUNT
            </p>

            <h3>
              {profile.name ||
                profile.full_name ||
                "Administrator"}
            </h3>

            <p>
              {profile.username ||
                profile.user_name ||
                "Admin account"}
            </p>

            <StatusChip variant="success">
              {String(profile.role || "ADMIN").toUpperCase()}
            </StatusChip>
          </div>

          <div className="adm-card">
            <div className="adm-card-heading">
              <div>
                <h3>Account details</h3>
                <p>
                  Information returned for the currently
                  signed-in user.
                </p>
              </div>
            </div>

            <div className="adm-info-row">
              <span>Display name</span>
              <strong>
                {profile.name ||
                  profile.full_name ||
                  "Administrator"}
              </strong>
            </div>

            <div className="adm-info-row">
              <span>Username</span>
              <strong>
                {profile.username ||
                  profile.user_name ||
                  "—"}
              </strong>
            </div>

            <div className="adm-info-row">
              <span>Role</span>
              <strong>
                {String(profile.role || "ADMIN").toUpperCase()}
              </strong>
            </div>

            <div className="adm-info-row">
              <span>Account created</span>
              <strong>{profile.created_at || "—"}</strong>
            </div>

            <div className="adm-info-row">
              <span>Account status</span>

              <StatusChip
                variant={
                  Number(profile.is_active) === 0
                    ? "danger"
                    : "success"
                }
              >
                {Number(profile.is_active) === 0
                  ? "INACTIVE"
                  : "ACTIVE"}
              </StatusChip>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}