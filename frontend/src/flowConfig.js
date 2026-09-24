// ============================================================
// SMART STUDENT BUS TRACKER
// Application Flow Configuration
// ============================================================

export const parentMenu = [
  {
    id: "menu",
    label: "Menu",
  },
  {
    id: "bus-schedule",
    label: "Bus Schedule",
  },
  {
    id: "live-location",
    label: "Live Bus Location",
  },
  {
    id: "notifications",
    label: "Notifications",
  },
  {
    id: "my-profile",
    label: "My Profile",
  },
  {
    id: "about",
    label: "About App",
  },
  {
    id: "app-tour",
    label: "App Tour Guide",
  },
  {
    id: "feedback",
    label: "Feedback",
  },
  {
    id: "contact",
    label: "Contact Us",
  },
  {
    id: "settings",
    label: "Settings",
  },
];


export const adminMenu = [
  {
    id: "menu",
    label: "Menu",
  },
  {
    id: "bus-schedule",
    label: "Update Bus Schedule",
  },
  {
    id: "live-location",
    label: "Live Bus Location",
  },
  {
    id: "feedback",
    label: "Feedback Collection",
  },
  {
    id: "my-profile",
    label: "My Profile",
  },
  {
    id: "about",
    label: "About App",
  },
  {
    id: "app-tour",
    label: "App Tour Guide",
  },
  {
    id: "event",
    label: "Event",
  },
  {
    id: "bus-management",
    label: "Bus Management",
  },
  {
    id: "student-management",
    label: "Student Management",
  },
  {
    id: "driver-management",
    label: "Driver Management",
  },
  {
    id: "route-management",
    label: "Route Management",
  },
  {
    id: "attendance",
    label: "Attendance",
  },
  {
    id: "reports",
    label: "Reports",
  },
  {
    id: "settings",
    label: "Settings",
  },
];


export const driverMenu = [
  {
    id: "live-location",
    label: "Live Bus Location",
  },
  {
    id: "trip",
    label: "Start / Stop Trip",
  },
  {
    id: "attendance",
    label: "Student Attendance",
  },
  {
    id: "face-recognition",
    label: "Face Recognition",
  },
  {
    id: "alert",
    label: "Alert",
  },
  {
    id: "my-profile",
    label: "My Profile",
  },
  {
    id: "settings",
    label: "Settings",
  },
];


export const commonSettings = [
  {
    id: "help",
    label: "Help",
  },
  {
    id: "logout",
    label: "Logout",
  },
  {
    id: "dark-mode",
    label: "Dark Mode",
  },
  {
    id: "language",
    label: "Language",
  },
];


export const parentSubMenus = {
  menu: [
    "Feedback",
    "Contact Us",
  ],

  "my-profile": [
    "Edit Profile",
    "Pick History",
  ],

  about: [
    "Development Team",
    "General Information",
  ],

  feedback: [
    "Options Given",
    "Text Field",
  ],

  contact: [
    "Gmail",
    "Phone",
  ],

  settings: commonSettings,
};


export const adminSubMenus = {
  "my-profile": [
    "Edit Profile",
  ],

  settings: commonSettings,

  "bus-management": [
    "Add New Bus",
    "Edit Bus",
    "Remove Bus",
  ],

  about: [
    "Development Team",
    "General Information",
  ],
};


export const driverSubMenus = {
  "my-profile": [
    "Edit Profile",
  ],

  settings: [
    "Help",
    "Logout",
  ],
};