import { useEffect, useRef, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";
import "./App.css";
import StopManagement from "./StopManagement";

import {
  parentMenu,
  adminMenu,
  driverMenu,
} from "./flowConfig";


// ============================================================
// FLOW MENU
// ============================================================

function FlowMenu({ items, onSelect, activeItem }) {
  return (
    <div className="flow-menu">
      {items.map((item) => (
        <button
          key={item.id}
          className={`flow-menu-item ${activeItem === item.id ? "active" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}


// ============================================================
// LIVE MAP VIEW
// ============================================================

function LiveLocationView({ location }) {
  const map = useMap();

  useEffect(() => {
    if (location) {
      map.setView(
        [location.latitude, location.longitude],
        Math.max(map.getZoom(), 16),
        { animate: true }
      );
    }
  }, [location, map]);

  return null;
}


// ============================================================
// MAP POSITION PERSISTENCE
// ============================================================

function PersistentMapView({ storageKey }) {
  const map = useMap();

  useEffect(() => {
    const saveMapView = () => {
      const center = map.getCenter();

      localStorage.setItem(
        storageKey,
        JSON.stringify({
          latitude: center.lat,
          longitude: center.lng,
          zoom: map.getZoom(),
        })
      );
    };

    map.on("moveend", saveMapView);
    map.on("zoomend", saveMapView);

    return () => {
      map.off("moveend", saveMapView);
      map.off("zoomend", saveMapView);
    };
  }, [map, storageKey]);

  return null;
}

function getSavedMapView(storageKey, fallbackCenter, fallbackZoom) {
  try {
    const saved = localStorage.getItem(storageKey);

    if (saved) {
      const parsed = JSON.parse(saved);

      if (
        Number.isFinite(parsed.latitude) &&
        Number.isFinite(parsed.longitude) &&
        Number.isFinite(parsed.zoom)
      ) {
        return {
          center: [parsed.latitude, parsed.longitude],
          zoom: parsed.zoom,
        };
      }
    }
  } catch (error) {
    console.error("Unable to restore saved map view:", error);
  }

  return {
    center: fallbackCenter,
    zoom: fallbackZoom,
  };
}


// ============================================================
// APP
// ============================================================

function App() {

  // ============================================================
  // BASIC APPLICATION STATE
  // ============================================================

  const [showSplash, setShowSplash] = useState(true);

  const [selectedRole, setSelectedRole] = useState(() => {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      return null;
    }

    try {
      const user = JSON.parse(savedUser);

      if (user.role === "PARENT") {
        return "PARENT_HOME";
      }

      if (user.role === "DRIVER") {
        return "DRIVER_HOME";
      }

      if (user.role === "ADMIN") {
        return "ADMIN_HOME";
      }

      return null;
    } catch {
      return null;
    }
  });

  const [selectedMenu, setSelectedMenu] = useState(null);

  const [travelStatus, setTravelStatus] =
    useState("COMING");

  const [travelStatusLoading, setTravelStatusLoading] =
    useState(false);


  // ============================================================
  // PARENT CALENDAR STATE
  // ============================================================

  const [attendanceHistory, setAttendanceHistory] =
    useState([]);

  const [attendanceHistoryLoading, setAttendanceHistoryLoading] =
    useState(false);

  const [calendarMonth, setCalendarMonth] =
    useState(new Date());


  // ============================================================
  // LOGIN STATE
  // ============================================================

  const [username, setUsername] = useState("");

  const [password, setPassword] = useState("");


  // ============================================================
  // NOTIFICATION STATE
  // ============================================================

  const [notifications, setNotifications] = useState([]);

  const [unreadNotificationCount, setUnreadNotificationCount] =
    useState(0);

  const [notificationsLoading, setNotificationsLoading] =
    useState(false);


  // ============================================================
  // CAMERA STATE
  // ============================================================

  const videoRef = useRef(null);

  const streamRef = useRef(null);

  const [cameraActive, setCameraActive] = useState(false);


  // ============================================================
  // FACE DETECTION STATE
  // ============================================================

  const [detectedFaces, setDetectedFaces] = useState([]);

  const [detecting, setDetecting] = useState(false);


  // ============================================================
  // FACE RECOGNITION STATE
  // ============================================================

  const [recognizedFaces, setRecognizedFaces] = useState([]);


  // ============================================================
  // ATTENDANCE STATE
  // ============================================================

  const [attendanceMessage, setAttendanceMessage] =
    useState("");

  const [attendanceMarked, setAttendanceMarked] =
    useState({});


  // ============================================================
  // FACE REGISTRATION STATE
  // ============================================================

  const [registrationStatus, setRegistrationStatus] =
    useState("");

  const [registering, setRegistering] =
    useState(false);


  // ============================================================
  // STUDENT MANAGEMENT STATE
  // ============================================================

  const [students, setStudents] =
    useState([]);

  // ============================================================
  // ROUTE STATE
  // ============================================================

  const [routes, setRoutes] =
    useState([]);

  const [routesLoading, setRoutesLoading] =
    useState(false);

  const [studentsLoading, setStudentsLoading] =
    useState(false);

  const [studentFormOpen, setStudentFormOpen] =
    useState(false);

  const [studentCreating, setStudentCreating] =
    useState(false);

  const [studentCreateMessage, setStudentCreateMessage] =
    useState("");

  const [createdParentCredentials, setCreatedParentCredentials] =
    useState(null);

  const [studentForm, setStudentForm] =
    useState({
      name: "",
      class_name: "",
      father_name: "",
      mother_name: "",
      phone: "",
      email: "",
      parent_username: "",
      parent_password: "",
    });

  const [selectedStudentId, setSelectedStudentId] =
    useState(null);

  const [selectedStudentName, setSelectedStudentName] =
    useState("");

  const [faceRegistrationOpen, setFaceRegistrationOpen] =
    useState(false);


  // ============================================================
  // TRIP STATE
  // ============================================================

  const [tripId, setTripId] = useState(null);

  const [tripStatus, setTripStatus] =
    useState("NOT_STARTED");


  // ============================================================
  // GPS STATE
  // ============================================================

  const [driverLocation, setDriverLocation] =
    useState(null);

  const [gpsStatus, setGpsStatus] =
    useState("GPS not started");

  const gpsIntervalRef =
    useRef(null);

  // Stores the browser watchPosition() ID.
  const lastGpsUploadRef =
    useRef(0);

  /*
   * IMPORTANT:
   *
   * React state updates asynchronously.
   *
   * We therefore keep the active trip ID in a ref as well.
   *
   * This allows GPS to immediately use the exact trip ID
   * returned by the backend after Start Trip.
   */
  const activeTripIdRef =
    useRef(null);


  // ============================================================
  // LIVE BUS LOCATION STATE
  // ============================================================

  const [busLocation, setBusLocation] =
    useState(null);

  const [busLocationStatus, setBusLocationStatus] =
    useState("Waiting for live bus location");


  // ============================================================
  // DRIVER TRAVEL STATUS STATE
  // ============================================================

  const [todayTravelStudents, setTodayTravelStudents] =
    useState([]);

  const [travelStudentsLoading, setTravelStudentsLoading] =
    useState(false);


  // ============================================================
  // CURRENT FLOW MENU
  // ============================================================

  const currentMenu =
    selectedRole === "PARENT_HOME"
      ? parentMenu
      : selectedRole === "ADMIN_HOME"
        ? adminMenu
        : selectedRole === "DRIVER_HOME"
          ? driverMenu
          : [];


  // ============================================================
  // CENTRAL API REQUEST HANDLER
  // Automatically logs out when the JWT has expired.
  // ============================================================

  const apiFetch = async (url, options = {}) => {

    const response = await fetch(url, options);

    if (response.status === 401) {

      try {

        const errorData = await response.clone().json();

        const message =
          String(errorData.message || "").toLowerCase();

        const isExpired =
          message.includes("expired") ||
          message.includes("token") ||
          message.includes("unauthorized");

        if (isExpired) {
          handleSessionExpired();
        }

      } catch (error) {

        console.error(
          "Unable to read authentication error:",
          error
        );

        handleSessionExpired();

      }

    }

    return response;

  };


  // ============================================================
  // SPLASH SCREEN TIMER
  // ============================================================

  useEffect(() => {

    const timer = setTimeout(() => {

      setShowSplash(false);

    }, 2000);


    return () => {

      clearTimeout(timer);

    };

  }, []);


  // ============================================================
  // AUTOMATIC JWT EXPIRY CHECK
  // ============================================================

  useEffect(() => {

    const checkTokenExpiry = () => {

      const token =
        localStorage.getItem("token");

      if (!token) {
        return;
      }

      try {

        const parts = token.split(".");

        if (parts.length !== 3) {

          handleSessionExpired();
          return;

        }

        const payload =
          JSON.parse(
            atob(
              parts[1]
                .replace(/-/g, "+")
                .replace(/_/g, "/")
            )
          );

        const expiryTime =
          Number(payload.exp) * 1000;

        if (
          !Number.isFinite(expiryTime) ||
          Date.now() >= expiryTime
        ) {

          handleSessionExpired();

        }

      } catch (error) {

        console.error(
          "Invalid authentication token:",
          error
        );

        handleSessionExpired();

      }

    };

    // Check immediately when the application loads.
    checkTokenExpiry();

    // Also check periodically while the application is open.
    const interval =
      setInterval(
        checkTokenExpiry,
        30000
      );

    return () => {

      clearInterval(interval);

    };

  }, [selectedRole]);


  // ============================================================
  // CAMERA + GPS CLEANUP
  // ============================================================

  useEffect(() => {

    return () => {

      if (streamRef.current) {

        streamRef.current
          .getTracks()
          .forEach((track) => track.stop());

      }


      if (gpsIntervalRef.current !== null) {

        navigator.geolocation?.clearWatch(
          gpsIntervalRef.current
        );

        gpsIntervalRef.current = null;

      }

    };

  }, []);


  // ============================================================
  // LOAD PARENT NOTIFICATIONS
  // ============================================================

  const loadParentNotifications = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setNotificationsLoading(true);

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/notifications",
          {
            method: "GET",

            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        console.error(
          data.message ||
          "Unable to load notifications"
        );

        return;

      }


      setNotifications(
        data.notifications || []
      );


      setUnreadNotificationCount(
        data.unread_count || 0
      );

    } catch (error) {

      console.error(
        "Notification loading error:",
        error
      );

    } finally {

      setNotificationsLoading(false);

    }

  };


  // ============================================================
  // LOAD ATTENDANCE WHEN PARENT OPENS DASHBOARD
  // ============================================================

  useEffect(() => {

    if (
      selectedRole !== "PARENT_HOME"
    ) {
      return;
    }

    loadAttendanceHistory();

  }, [selectedRole]);


  // ============================================================
  // LOAD NOTIFICATIONS WHEN PARENT LOGS IN
  // ============================================================

  useEffect(() => {

    if (
      selectedRole !== "PARENT_HOME"
    ) {

      return;

    }


    loadParentNotifications();

  }, [selectedRole]);


  // ============================================================
  // REFRESH ATTENDANCE WHEN CALENDAR IS OPENED
  // ============================================================

  useEffect(() => {

    if (
      selectedRole !== "PARENT_HOME" ||
      selectedMenu !== "calendar"
    ) {
      return;
    }

    loadAttendanceHistory();

  }, [selectedRole, selectedMenu]);


  // ============================================================
  // LOAD STUDENT ATTENDANCE HISTORY
  // ============================================================

  const loadAttendanceHistory = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setAttendanceHistoryLoading(true);

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/attendance/student/1",
          {
            method: "GET",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        console.error(
          data.message ||
          "Unable to load attendance history"
        );

        return;
      }

      setAttendanceHistory(
        data.attendance || []
      );

    } catch (error) {

      console.error(
        "Attendance history loading error:",
        error
      );

    } finally {

      setAttendanceHistoryLoading(false);

    }

  };


  // ============================================================
  // CALENDAR HELPERS
  // ============================================================

  const getAttendanceDateSet = () => {

    const dates = new Set();

    attendanceHistory.forEach((record) => {

      const status =
        String(record.status || "")
          .trim()
          .toUpperCase();

      if (status !== "PRESENT") {
        return;
      }

      // attendance_date is the authoritative calendar date.
      // recognized_at is only a fallback for older records.
      const rawDate =
        record.attendance_date ||
        (
          record.recognized_at
            ? String(record.recognized_at).substring(0, 10)
            : ""
        );

      const date =
        String(rawDate)
          .trim()
          .substring(0, 10);

      if (/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        dates.add(date);
      }

    });

    return dates;

  };


  const getCalendarDays = () => {

    const year =
      calendarMonth.getFullYear();

    const month =
      calendarMonth.getMonth();

    const firstDay =
      new Date(year, month, 1).getDay();

    const daysInMonth =
      new Date(year, month + 1, 0).getDate();

    const days = [];

    for (let index = 0; index < firstDay; index++) {
      days.push(null);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }

    return days;

  };


  const formatCalendarDate = (year, month, day) => {

    return [
      year,
      String(month + 1).padStart(2, "0"),
      String(day).padStart(2, "0"),
    ].join("-");

  };


  const goToPreviousMonth = () => {

    setCalendarMonth(
      (previous) =>
        new Date(
          previous.getFullYear(),
          previous.getMonth() - 1,
          1
        )
    );

  };


  const goToNextMonth = () => {

    setCalendarMonth(
      (previous) =>
        new Date(
          previous.getFullYear(),
          previous.getMonth() + 1,
          1
        )
    );

  };


  const goToCurrentMonth = () => {

    setCalendarMonth(
      new Date()
    );

  };


  // ============================================================
  // LOAD LIVE BUS LOCATION
  // ============================================================

  const loadLiveBusLocation = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {

      setBusLocation(null);

      setBusLocationStatus(
        "Please login to view live bus location."
      );

      return;

    }

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/locations/bus/1/latest",
          {
            method: "GET",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        console.error(
          "Live bus location request failed:",
          data
        );

        setBusLocation(null);

        setBusLocationStatus(
          data.message ||
          "Unable to load live bus location."
        );

        return;

      }


      if (data.location) {

        setBusLocation(
          data.location
        );

        setBusLocationStatus(
          "LIVE • Bus location updating"
        );

      } else {

        setBusLocation(null);

        setBusLocationStatus(
          "Bus is not currently on an active trip."
        );

      }

    } catch (error) {

      console.error(
        "Live bus location error:",
        error
      );

      setBusLocationStatus(
        "Unable to connect to live location service."
      );

    }

  };


  // ============================================================
  // POLL LIVE BUS LOCATION FOR PARENT / ADMIN
  // ============================================================

  useEffect(() => {

    const isTrackingDashboard =
      selectedRole === "PARENT_HOME" ||
      selectedRole === "ADMIN_HOME";


    if (!isTrackingDashboard) {

      setBusLocation(null);

      setBusLocationStatus(
        "Waiting for live bus location"
      );

      return;

    }


    loadLiveBusLocation();


    const interval =
      setInterval(
        loadLiveBusLocation,
        3000
      );


    return () => {

      clearInterval(interval);

    };

  }, [selectedRole]);


  // ============================================================
  // START CAMERA
  // ============================================================

  const startCamera = async () => {

    try {

      if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
      ) {

        alert(
          "Your browser does not support camera access."
        );

        return;

      }


      const stream =
        await navigator.mediaDevices.getUserMedia({

          video: true,

          audio: false,

        });


      streamRef.current = stream;


      if (videoRef.current) {

        videoRef.current.srcObject =
          stream;

      }


      setCameraActive(true);

      setAttendanceMessage("");

      setRegistrationStatus("");

    } catch (error) {

      console.error(
        "Camera error:",
        error
      );


      alert(
        "Unable to access the laptop camera. " +
        "Please allow camera permission."
      );

    }

  };


  // ============================================================
  // STOP CAMERA
  // ============================================================

  const stopCamera = () => {

    if (streamRef.current) {

      streamRef.current
        .getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;

    }


    if (videoRef.current) {

      videoRef.current.srcObject = null;

    }


    setCameraActive(false);

    setDetectedFaces([]);

    setRecognizedFaces([]);

    setDetecting(false);

  };


  // ============================================================
  // CAPTURE CAMERA IMAGE
  // ============================================================

  const captureCameraImage = () => {

    if (!videoRef.current) {

      return null;

    }


    const video =
      videoRef.current;


    if (
      video.videoWidth === 0 ||
      video.videoHeight === 0
    ) {

      return null;

    }


    const canvas =
      document.createElement("canvas");


    canvas.width =
      video.videoWidth;

    canvas.height =
      video.videoHeight;


    const context =
      canvas.getContext("2d");


    context.drawImage(
      video,
      0,
      0,
      canvas.width,
      canvas.height
    );


    return canvas.toDataURL(
      "image/jpeg",
      0.9
    );

  };


  // ============================================================
  // FACE DETECTION
  // ============================================================

  const detectFace = async () => {

    if (!videoRef.current) {

      return;

    }


    if (!cameraActive) {

      return;

    }


    const image =
      captureCameraImage();


    if (!image) {

      return;

    }


    try {

      const token =
        localStorage.getItem("token");


      if (!token) {

        return;

      }


      const response =
        await apiFetch(
          "http://localhost:5000/api/face/detect",
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,

            },

            body: JSON.stringify({

              image: image,

            }),

          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        console.error(
          data.message ||
          "Face detection failed"
        );

        return;

      }


      setDetectedFaces(
        data.faces || []
      );

    } catch (error) {

      console.error(
        "Detection error:",
        error
      );

    }

  };


  // ============================================================
  // MARK ATTENDANCE
  // ============================================================

  const markStudentAttendance = async (
    studentId,
    confidence
  ) => {

    const token =
      localStorage.getItem("token");


    if (!token) {

      return false;

    }


    /*
     * Use the ref first because it contains the
     * latest trip ID immediately after Start Trip.
     */
    const activeTripId =
      activeTripIdRef.current || tripId;


    if (!activeTripId) {

      setAttendanceMessage(
        "Start a trip before marking attendance."
      );

      return false;

    }


    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/attendance/mark",
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,

            },

            body: JSON.stringify({

              student_id:
                studentId,

              trip_id:
                activeTripId,

              confidence:
                confidence,

            }),

          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        setAttendanceMessage(
          data.message ||
          "Unable to mark attendance."
        );

        return false;

      }


      setAttendanceMessage(
        data.message ||
        "Attendance marked successfully."
      );


      return true;

    } catch (error) {

      console.error(
        "Attendance error:",
        error
      );


      setAttendanceMessage(
        "Unable to connect to attendance API."
      );


      return false;

    }

  };


  // ============================================================
  // FACE RECOGNITION
  // ============================================================

  const recognizeFace = async () => {

    if (!videoRef.current) {

      return;

    }


    if (!cameraActive) {

      return;

    }


    const image =
      captureCameraImage();


    if (!image) {

      return;

    }


    try {

      const token =
        localStorage.getItem("token");


      if (!token) {

        return;

      }


      const response =
        await apiFetch(
          "http://localhost:5000/api/face/recognize",
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,

            },

            body: JSON.stringify({

              image: image,

            }),

          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        console.error(
          data.message ||
          "Face recognition failed"
        );

        return;

      }


      const faces =
        data.faces || [];


      setRecognizedFaces(
        faces
      );


      const recognizedStudent =
        faces.find(
          (face) =>
            face.recognized === true
        );


      if (!recognizedStudent) {

        return;

      }


      const studentId =
        recognizedStudent.student_id;


      if (
        attendanceMarked[studentId]
      ) {

        return;

      }


      const success =
        await markStudentAttendance(
          studentId,
          recognizedStudent.similarity
        );


      if (success) {

        setAttendanceMarked(
          (previous) => ({

            ...previous,

            [studentId]: true,

          })
        );

      }

    } catch (error) {

      console.error(
        "Recognition error:",
        error
      );

    }

  };


  // ============================================================
  // RUN DETECTION + RECOGNITION
  // ============================================================

  useEffect(() => {

    if (!cameraActive) {

      return;

    }


    setDetecting(true);


    const interval =
      setInterval(() => {

        detectFace();

        if (selectedRole === "DRIVER_HOME") {
          recognizeFace();
        }

      }, 1000);


    return () => {

      clearInterval(interval);

      setDetecting(false);

    };

  }, [cameraActive]);


  // ============================================================
  // FACE REGISTRATION
  // ============================================================

  const registerStudentFace = async () => {

    if (!selectedStudentId) {

      alert(
        "Please select a student before registering a face."
      );

      return;

    }

    if (!cameraActive) {

      alert(
        "Please start the camera first."
      );

      return;

    }


    if (
      detectedFaces.length !== 1
    ) {

      alert(
        "Please make sure exactly one face is visible."
      );

      return;

    }


    const image =
      captureCameraImage();


    if (!image) {

      alert(
        "Unable to capture camera image."
      );

      return;

    }


    const token =
      localStorage.getItem("token");


    if (!token) {

      alert(
        "Please login as Admin."
      );

      return;

    }


    setRegistering(true);

    setRegistrationStatus(
      "Registering face..."
    );


    try {

      const response =
        await apiFetch(
          `http://localhost:5000/api/face-registration/${selectedStudentId}`,
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,

            },

            body: JSON.stringify({

              image: image,

            }),

          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        setRegistrationStatus(
          data.message ||
          "Face registration failed."
        );

        return;

      }


      setAttendanceMarked({});


      setRegistrationStatus(
        `✓ Face registered successfully for ${data.student.name}`
      );


    } catch (error) {

      console.error(
        "Registration error:",
        error
      );


      setRegistrationStatus(
        "Unable to connect to the backend."
      );

    } finally {

      setRegistering(false);

    }

  };


  // ============================================================
  // STUDENT MANAGEMENT
  // ============================================================

  const loadStudents = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setStudentsLoading(true);

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/students",
          {
            method: "GET",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        setStudentCreateMessage(
          data.message ||
          "Unable to load students."
        );

        return;
      }

      setStudents(
        data.students || []
      );

    } catch (error) {

      console.error(
        "Student loading error:",
        error
      );

      setStudentCreateMessage(
        "Unable to connect to the student service."
      );

    } finally {

      setStudentsLoading(false);

    }

  };


  // ============================================================
  // LOAD ROUTES
  // ============================================================

  const loadRoutes = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setRoutesLoading(true);

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/routes",
          {
            method: "GET",

            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        console.error(
          data.message ||
          "Unable to load routes."
        );

        return;
      }

      setRoutes(
        data.routes || []
      );

    } catch (error) {

      console.error(
        "Route loading error:",
        error
      );

    } finally {

      setRoutesLoading(false);

    }

  };


  const resetStudentForm = () => {

    setStudentForm({
      name: "",
      class_name: "",
      father_name: "",
      mother_name: "",
      phone: "",
      email: "",
      parent_username: "",
      parent_password: "",
    });

    setStudentCreateMessage("");

    setCreatedParentCredentials(null);

  };


  const createStudent = async (event) => {

    event.preventDefault();

    const token =
      localStorage.getItem("token");

    if (!token) {

      alert(
        "Please login as Admin."
      );

      return;

    }

    if (!studentForm.name.trim()) {

      setStudentCreateMessage(
        "Student name is required."
      );

      return;

    }

    if (!studentForm.class_name.trim()) {

      setStudentCreateMessage(
        "Class is required."
      );

      return;

    }

    if (
      !studentForm.father_name.trim() &&
      !studentForm.mother_name.trim() &&
      !studentForm.parent_username.trim()
    ) {

      setStudentCreateMessage(
        "At least one parent name is required, unless an existing Parent ID is used."
      );

      return;

    }

    if (!studentForm.parent_password.trim()) {

      setStudentCreateMessage(
        "Parent password is required."
      );

      return;

    }

    if (studentForm.parent_password.trim().length < 6) {

      setStudentCreateMessage(
        "Parent password must be at least 6 characters."
      );

      return;

    }

    setStudentCreating(true);

    setStudentCreateMessage(
      "Creating student and family account..."
    );

    setCreatedParentCredentials(null);

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/students",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,
            },

            body: JSON.stringify(
              studentForm
            ),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        setStudentCreateMessage(
          data.message ||
          data.error ||
          "Unable to create student."
        );

        return;

      }

      const newStudentId =
        data.student?.id ||
        data.next_step?.student_id;

      setStudentCreateMessage(
        "Student created successfully. Face registration is ready."
      );

      setCreatedParentCredentials(
        data.parent || null
      );

      setStudentFormOpen(false);

      await loadStudents();

      if (newStudentId) {

        setSelectedStudentId(
          newStudentId
        );

        setSelectedStudentName(
          data.student?.name || ""
        );

        setFaceRegistrationOpen(true);

        setSelectedMenu(
          "student-management"
        );

      }

      setStudentForm({
        name: "",
        class_name: "",
        father_name: "",
        mother_name: "",
        phone: "",
        email: "",
        parent_username: "",
        parent_password: "",
      });

    } catch (error) {

      console.error(
        "Create student error:",
        error
      );

      setStudentCreateMessage(
        "Unable to connect to the backend."
      );

    } finally {

      setStudentCreating(false);

    }

  };


  // ============================================================
  // PERMANENTLY DELETE STUDENT
  // ============================================================

  const deleteStudent = async (student) => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      alert("Please login as Admin.");
      return;
    }

    const firstConfirmation =
      window.confirm(
        `PERMANENTLY DELETE ${student.name}?\n\n` +
        `Student Code: ${student.student_code}\n\n` +
        `This will permanently remove the student, ` +
        `registered face, attendance history, ` +
        `travel status and student notifications.\n\n` +
        `The family/parent account will be preserved.\n\n` +
        `This action CANNOT be undone.`
      );

    if (!firstConfirmation) {
      return;
    }

    const confirmationCode =
      window.prompt(
        `Permanent deletion confirmation.\n\n` +
        `Type the student code exactly:\n\n` +
        `${student.student_code}`
      );

    if (confirmationCode !== student.student_code) {
      alert(
        "Deletion cancelled. Student code did not match."
      );
      return;
    }

    try {

      const response =
        await apiFetch(
          `http://localhost:5000/api/students/${student.id}`,
          {
            method: "DELETE",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        alert(
          data.message ||
          data.error ||
          "Unable to permanently delete student."
        );
        return;
      }

      if (selectedStudentId === student.id) {
        closeFaceRegistration();
      }

      await loadStudents();

      setStudentCreateMessage(
        data.message ||
        `${student.name} was permanently deleted.`
      );

    } catch (error) {

      console.error(
        "Permanent delete error:",
        error
      );

      alert(
        "Unable to connect to the backend."
      );

    }

  };


  const openFaceRegistration = (student) => {

    setSelectedStudentId(
      student.id
    );

    setSelectedStudentName(
      student.name
    );

    setFaceRegistrationOpen(true);

    setRegistrationStatus("");

    setSelectedMenu(
      "student-management"
    );

  };


  const closeFaceRegistration = () => {

    stopCamera();

    setFaceRegistrationOpen(false);

    setSelectedStudentId(null);

    setSelectedStudentName("");

    setRegistrationStatus("");

  };


  useEffect(() => {

    if (
      selectedRole !== "ADMIN_HOME"
    ) {
      return;
    }

    if (
      selectedMenu === "student-management" ||
      selectedMenu === "students"
    ) {

      loadStudents();

    }

    if (
      selectedMenu === "stop-management"
    ) {

      loadRoutes();

    }

  }, [selectedRole, selectedMenu]);


  // ============================================================
  // LOGIN
  // ============================================================

  const handleLogin = async () => {

    if (!username || !password) {

      alert(
        "Please enter username and password."
      );

      return;

    }


    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/auth/login",
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

            },

            body: JSON.stringify({

              username,
              password,

            }),

          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        alert(
          data.message ||
          "Login failed"
        );

        return;

      }


      localStorage.setItem(
        "token",
        data.token
      );


      localStorage.setItem(
        "user",
        JSON.stringify(
          data.user
        )
      );


      if (
        data.user.role ===
        "PARENT"
      ) {

        setSelectedRole(
          "PARENT_HOME"
        );

      } else if (
        data.user.role ===
        "DRIVER"
      ) {

        setSelectedRole(
          "DRIVER_HOME"
        );

      } else if (
        data.user.role ===
        "ADMIN"
      ) {

        setSelectedRole(
          "ADMIN_HOME"
        );

      }


      setSelectedMenu(null);

    } catch (error) {

      console.error(
        "Login error:",
        error
      );


      alert(
        "Unable to connect to the backend."
      );

    }

  };


  // ============================================================
  // LOGOUT
  // ============================================================

  // ============================================================
  // EXPIRED SESSION HANDLER
  // ============================================================

  const handleSessionExpired = () => {

    stopCamera();

    if (gpsIntervalRef.current !== null) {

      navigator.geolocation?.clearWatch(
        gpsIntervalRef.current
      );

      gpsIntervalRef.current = null;

    }

    activeTripIdRef.current = null;

    localStorage.removeItem("token");
    localStorage.removeItem("user");

    setUsername("");
    setPassword("");
    setSelectedMenu(null);
    setSelectedRole(null);

    setAttendanceMarked({});
    setAttendanceMessage("");
    setNotifications([]);
    setUnreadNotificationCount(0);

    setTripId(null);
    setTripStatus("NOT_STARTED");

    setDriverLocation(null);
    setBusLocation(null);
    setBusLocationStatus("Waiting for live bus location");
    setGpsStatus("GPS not started");

  };


  const logout = () => {

    handleSessionExpired();

  };


  // ============================================================
  // MENU SELECTION
  // ============================================================

  const handleMenuSelect =
    (menuId) => {

      setSelectedMenu(
        menuId
      );

      console.log(
        "Selected menu:",
        menuId
      );

    };


  // ============================================================
  // MARK NOTIFICATION AS READ
  // ============================================================

  const markNotificationRead =
    async (notificationId) => {

      const token =
        localStorage.getItem("token");


      if (!token) {

        return;

      }


      try {

        const response =
          await apiFetch(
            `http://localhost:5000/api/notifications/${notificationId}/read`,
            {

              method: "PUT",

              headers: {

                Authorization:
                  `Bearer ${token}`,

              },

            }
          );


        const data =
          await response.json();


        if (!response.ok) {

          console.error(
            data.message ||
            "Unable to mark notification as read"
          );

          return;

        }


        await loadParentNotifications();

      } catch (error) {

        console.error(
          "Read notification error:",
          error
        );

      }

    };


  // ============================================================
  // TRAVEL STATUS
  // ============================================================

  const loadTravelStatus = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setTravelStatusLoading(true);

    const travelDate =
      new Date()
        .toISOString()
        .split("T")[0];

    try {

      const response =
        await apiFetch(
          `http://localhost:5000/api/travel/status/1?travel_date=${travelDate}`,
          {
            method: "GET",

            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        console.error(
          data.message ||
          "Unable to load travel status"
        );

        return;
      }

      setTravelStatus(
        data.status || "COMING"
      );

    } catch (error) {

      console.error(
        "Travel status loading error:",
        error
      );

    } finally {

      setTravelStatusLoading(false);

    }

  };


  const updateTravelStatus =
    async (status) => {

      const token =
        localStorage.getItem(
          "token"
        );

      if (!token) {
        return;
      }

      setTravelStatus(status);

      const travelDate =
        new Date()
          .toISOString()
          .split("T")[0];

      try {

        const response =
          await apiFetch(
            "http://localhost:5000/api/travel/status",
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",

                Authorization:
                  `Bearer ${token}`,
              },

              body: JSON.stringify({
                student_id: 1,
                status: status,
                travel_date: travelDate,
              }),
            }
          );

        const data =
          await response.json();

        if (!response.ok) {

          setTravelStatus(null);

          alert(
            data.message ||
            "Unable to update travel status"
          );

          return;
        }

        setTravelStatus(
          data.status
        );

      } catch (error) {

        console.error(
          "Travel status error:",
          error
        );

        setTravelStatus(null);

        alert(
          "Unable to connect to backend."
        );

      }

    };


  // Load today's travel status when Parent Dashboard opens.
  useEffect(() => {

    if (
      selectedRole !== "PARENT_HOME"
    ) {
      return;
    }

    loadTravelStatus();

  }, [selectedRole]);


  // ============================================================
  // LOAD TODAY'S STUDENT TRAVEL STATUS
  // ============================================================

  const loadTodayTravelStudents = async () => {

    const token =
      localStorage.getItem("token");

    if (!token) {
      return;
    }

    setTravelStudentsLoading(true);

    const travelDate =
      new Date()
        .toISOString()
        .split("T")[0];

    try {

      const response =
        await apiFetch(
          `http://localhost:5000/api/travel/today?travel_date=${travelDate}`,
          {
            method: "GET",
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        console.error(
          data.message ||
          "Unable to load student travel status"
        );

        return;
      }

      setTodayTravelStudents(
        data.students || []
      );

    } catch (error) {

      console.error(
        "Travel students loading error:",
        error
      );

    } finally {

      setTravelStudentsLoading(false);

    }

  };


  // ============================================================
  // DRIVER TRAVEL STATUS SUMMARY
  // ============================================================

  const travelSummary = {
    coming: todayTravelStudents.filter(
      (student) => student.status === "COMING"
    ).length,

    notComing: todayTravelStudents.filter(
      (student) => student.status === "NOT_COMING"
    ).length,

    noStatus: todayTravelStudents.filter(
      (student) => !student.status
    ).length,
  };


  // Load today's travel status when Driver Dashboard opens.
  useEffect(() => {

    if (
      selectedRole !== "DRIVER_HOME"
    ) {
      return;
    }

    loadTodayTravelStudents();

  }, [selectedRole]);


  // Refresh today's travel status every 10 seconds.
  useEffect(() => {

    if (
      selectedRole !== "DRIVER_HOME"
    ) {
      return;
    }

    const interval =
      setInterval(() => {
        loadTodayTravelStudents();
      }, 10000);

    return () => {
      clearInterval(interval);
    };

  }, [selectedRole]);


  // ============================================================
  // LIVE DRIVER GPS
  // ============================================================

  /*
   * No driver coordinates are hard-coded here.
   * The browser supplies the actual device location.
   */

  const uploadLiveLocation = async (
    position,
    specificTripId = null
  ) => {

    const token =
      localStorage.getItem("token");

    const activeTripId =
      specificTripId ||
      activeTripIdRef.current ||
      tripId;

    if (!token || !activeTripId) {
      return;
    }

    const latitude =
      position.coords.latitude;

    const longitude =
      position.coords.longitude;

    const speed =
      position.coords.speed !== null &&
      position.coords.speed !== undefined
        ? position.coords.speed * 3.6
        : null;

    const accuracy =
      position.coords.accuracy;

    // Update the map immediately with the real device position.
    setDriverLocation({
      latitude,
      longitude,
      speed,
      accuracy,
      recordedAt: new Date().toISOString(),
    });

    setGpsStatus(
      `GPS LIVE • Accuracy ±${Math.round(accuracy)} m`
    );

    // Limit backend writes to roughly one every 3 seconds.
    const now = Date.now();

    if (
      now - lastGpsUploadRef.current < 3000
    ) {
      return;
    }

    lastGpsUploadRef.current = now;

    try {

      const response =
        await apiFetch(
          "http://localhost:5000/api/locations",
          {

            method: "POST",

            headers: {

              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,

            },

            body: JSON.stringify({

              trip_id:
                activeTripId,

              latitude:
                latitude,

              longitude:
                longitude,

              speed:
                speed,

            }),

          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        console.error(
          "Live GPS upload failed:",
          data
        );

        setGpsStatus(
          data.message ||
          "GPS is live, but location upload failed."
        );

        return;
      }

      console.log(
        "LIVE GPS LOCATION:",
        {
          latitude,
          longitude,
          accuracy,
          backend: data,
        }
      );

      setGpsStatus(
        `GPS LIVE • ±${Math.round(accuracy)} m • uploaded`
      );

    } catch (error) {

      console.error(
        "Live GPS network error:",
        error
      );

      setGpsStatus(
        "GPS is live, but backend connection failed."
      );

    }

  };


  // ============================================================
  // RESTORE ACTIVE DRIVER TRIP
  // ============================================================

  const restoreActiveTrip = async () => {

    const token = localStorage.getItem("token");

    if (!token) {
      return;
    }

    try {

      const response = await apiFetch(
        "http://localhost:5000/api/trips/active",
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        console.error(
          "Active trip restore failed:",
          data
        );
        return;
      }

      if (
        data.active &&
        data.trip &&
        data.trip.status === "IN_PROGRESS"
      ) {

        const activeTripId = data.trip.id;

        setTripId(activeTripId);
        activeTripIdRef.current = activeTripId;
        setTripStatus("IN_PROGRESS");

        setAttendanceMessage(
          "Active trip restored after refresh."
        );

        startDriverGPS(activeTripId);

      } else {

        setTripId(null);
        activeTripIdRef.current = null;
        setTripStatus("NOT_STARTED");

      }

    } catch (error) {

      console.error(
        "Active trip restore error:",
        error
      );

    }

  };


  // ============================================================
  // RESTORE ACTIVE TRIP WHEN DRIVER DASHBOARD LOADS
  // ============================================================

  useEffect(() => {

    if (selectedRole !== "DRIVER_HOME") {
      return;
    }

    restoreActiveTrip();

  }, [selectedRole]);


  // ============================================================
  // START DRIVER GPS
  // ============================================================

  const startDriverGPS =
    (specificTripId = null) => {

      const activeTripId =
        specificTripId ||
        activeTripIdRef.current ||
        tripId;

      if (!activeTripId) {

        setGpsStatus(
          "Start a trip before GPS."
        );

        return;

      }

      if (!navigator.geolocation) {

        setGpsStatus(
          "This browser does not provide device geolocation."
        );

        return;

      }

      activeTripIdRef.current =
        activeTripId;

      // Stop an older watcher first.
      if (gpsIntervalRef.current !== null) {

        navigator.geolocation.clearWatch(
          gpsIntervalRef.current
        );

        gpsIntervalRef.current = null;

      }

      lastGpsUploadRef.current = 0;

      setGpsStatus(
        "Requesting your device's live location..."
      );

      /*
       * watchPosition continuously receives the actual
       * device location. There are no fixed coordinates.
       */
      const watchId =
        navigator.geolocation.watchPosition(

          (position) => {

            uploadLiveLocation(
              position,
              activeTripId
            );

          },

          (error) => {

            console.error(
              "LIVE GPS ERROR:",
              error
            );

            if (error.code === 1) {

              setGpsStatus(
                "Location permission denied. Allow location access for this site."
              );

            } else if (error.code === 2) {

              setGpsStatus(
                "Device location is unavailable. Check Windows Location Services."
              );

            } else if (error.code === 3) {

              setGpsStatus(
                "Device location timed out. Waiting for another GPS update..."
              );

            } else {

              setGpsStatus(
                "Unable to read the device's live location."
              );

            }

          },

          {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0,
          }

        );

      gpsIntervalRef.current =
        watchId;

    };


  // ============================================================
  // STOP DRIVER GPS
  // ============================================================

  const stopDriverGPS =
    () => {

      if (gpsIntervalRef.current !== null) {

        navigator.geolocation.clearWatch(
          gpsIntervalRef.current
        );

        gpsIntervalRef.current = null;

      }

      activeTripIdRef.current =
        null;

      lastGpsUploadRef.current =
        0;

      setGpsStatus(
        "GPS stopped."
      );

    };


  // ============================================================
  // START TRIP
  // ============================================================

  const startTrip =
    async () => {

      const token =
        localStorage.getItem(
          "token"
        );


      if (!token) {

        alert(
          "Please login first."
        );

        return;

      }


      try {

        const response =
          await apiFetch(
            "http://localhost:5000/api/trips/start",
            {

              method: "POST",

              headers: {

                "Content-Type":
                  "application/json",

                Authorization:
                  `Bearer ${token}`,

              },

              body: JSON.stringify({

                bus_id: 1,

                route_id: 1,

                trip_type:
                  "PICKUP",

              }),

            }
          );


        const data =
          await response.json();


        if (!response.ok) {

          alert(
            data.message ||
            "Unable to start trip"
          );

          return;

        }


        /*
         * Get the actual trip ID returned
         * from Flask.
         */

        const newTripId =
          data.trip_id ||
          data.trip?.id ||
          data.id ||
          null;


        if (!newTripId) {

          console.error(
            "Trip API response:",
            data
          );


          alert(
            "Trip started, but the backend did not return a trip ID."
          );

          return;

        }


        /*
         * IMPORTANT:
         *
         * Store the trip ID in both React state
         * and the ref.
         */

        setTripId(
          newTripId
        );


        activeTripIdRef.current =
          newTripId;


        setTripStatus(
          "IN_PROGRESS"
        );


        setAttendanceMarked({});


        setAttendanceMessage(
          "Trip started successfully."
        );


        /*
         * Immediately start GPS using newTripId.
         *
         * We do NOT wait for React's setTripId().
         */

        startDriverGPS(
          newTripId
        );


        alert(
          `Trip started successfully!\nTrip ID: ${newTripId}\nGPS starting...`
        );


      } catch (error) {

        console.error(
          "Start trip error:",
          error
        );


        alert(
          "Unable to connect to backend."
        );

      }

    };


  // ============================================================
  // STOP TRIP
  // ============================================================

  const stopTrip =
    async () => {

      const token =
        localStorage.getItem(
          "token"
        );


      if (!token) {

        alert(
          "Please login first."
        );

        return;

      }


      const activeTripId =
        activeTripIdRef.current ||
        tripId;


      if (!activeTripId) {

        alert(
          "There is no active trip."
        );

        return;

      }


      try {

        const response =
          await apiFetch(
            `http://localhost:5000/api/trips/${activeTripId}/stop`,
            {

              method: "POST",

              headers: {

                Authorization:
                  `Bearer ${token}`,

              },

            }
          );


        const data =
          await response.json();


        if (!response.ok) {

          alert(
            data.message ||
            "Unable to stop trip"
          );

          return;

        }


        /*
         * Stop GPS.
         */

        stopDriverGPS();


        setTripStatus(
          "COMPLETED"
        );


        setGpsStatus(
          "Trip completed. GPS stopped."
        );


        setAttendanceMessage(
          "Trip completed successfully."
        );


        alert(
          "Trip completed successfully."
        );


      } catch (error) {

        console.error(
          "Stop trip error:",
          error
        );


        alert(
          "Unable to connect to backend."
        );

      }

    };


  // ============================================================
  // SPLASH SCREEN
  // ============================================================

  if (showSplash) {

    return (

      <main className="splash-screen">

        <div className="splash-content">

          <div className="splash-icon">
            🚌
          </div>


          <h1>
            Smart Student
            <br />
            Bus Tracker
          </h1>


          <p>
            Safe journeys. Smarter tracking.
          </p>

        </div>

      </main>

    );

  }


  // ============================================================
  // ROLE SELECTION
  // ============================================================

  if (!selectedRole) {

    return (

      <main className="role-page">

        <div className="role-container">

          <div className="brand-section">

            <div className="brand-icon">
              🚌
            </div>


            <h1>
              Smart Student
              <br />
              Bus Tracker
            </h1>


            <p>
              Choose your account type
            </p>

          </div>


          <div className="role-cards">

            <button
              className="role-card"
              onClick={() =>
                setSelectedRole(
                  "PARENT_LOGIN"
                )
              }
            >

              <span className="role-icon">
                👨‍👩‍👧
              </span>


              <div>

                <h2>
                  Parent
                </h2>

                <p>
                  Track your child's bus
                  and attendance.
                </p>

              </div>


              <span className="role-arrow">
                →
              </span>

            </button>


            <button
              className="role-card"
              onClick={() =>
                setSelectedRole(
                  "DRIVER_LOGIN"
                )
              }
            >

              <span className="role-icon">
                🚌
              </span>


              <div>

                <h2>
                  Bus Driver
                </h2>

                <p>
                  Manage trips and
                  student attendance.
                </p>

              </div>


              <span className="role-arrow">
                →
              </span>

            </button>


            <button
              className="role-card"
              onClick={() =>
                setSelectedRole(
                  "ADMIN_LOGIN"
                )
              }
            >

              <span className="role-icon">
                🛠️
              </span>


              <div>

                <h2>
                  Admin
                </h2>

                <p>
                  Manage the complete
                  bus tracking system.
                </p>

              </div>


              <span className="role-arrow">
                →
              </span>

            </button>

          </div>

        </div>

      </main>

    );

  }


  // ============================================================
  // LOGIN PAGE
  // ============================================================

  if (
    selectedRole ===
      "PARENT_LOGIN" ||
    selectedRole ===
      "DRIVER_LOGIN" ||
    selectedRole ===
      "ADMIN_LOGIN"
  ) {

    let roleTitle =
      "Login";

    let roleIcon =
      "🔐";


    if (
      selectedRole ===
      "PARENT_LOGIN"
    ) {

      roleTitle =
        "Parent Login";

      roleIcon =
        "👨‍👩‍👧";

    }


    if (
      selectedRole ===
      "DRIVER_LOGIN"
    ) {

      roleTitle =
        "Driver Login";

      roleIcon =
        "🚌";

    }


    if (
      selectedRole ===
      "ADMIN_LOGIN"
    ) {

      roleTitle =
        "Admin Login";

      roleIcon =
        "🛠️";

    }


    return (

      <main className="login-page">

        <div className="login-card">

          <button
            className="back-button"
            onClick={() => {

              setSelectedRole(
                null
              );

              setUsername("");

              setPassword("");

            }}
          >
            ← Back
          </button>


          <div className="login-icon">
            {roleIcon}
          </div>


          <h1>
            {roleTitle}
          </h1>


          <p className="login-subtitle">
            Sign in to continue
          </p>


          <div className="login-form">

            <label>
              Username
            </label>


            <input
              type="text"
              placeholder="Enter username"
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value
                )
              }
            />


            <label>
              Password
            </label>


            <input
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value
                )
              }
            />


            <button
              className="login-button"
              onClick={
                handleLogin
              }
            >
              Login
            </button>

          </div>

        </div>

      </main>

    );

  }


  // ============================================================
  // PARENT DASHBOARD
  // ============================================================

  const parentMapView = getSavedMapView(
    "smart-student-parent-map-view",
    [17.289612892928957, 76.86886054620065],
    15
  );

  if (
    selectedRole ===
    "PARENT_HOME"
  ) {

    return (
      <main className="parent-admin-dashboard">

        <header className="admin-style-header">
          <div className="admin-style-brand">
            <div className="admin-style-logo">🚌</div>
            <div>
              <p>Smart Student Bus</p>
              <h1>Parent</h1>
            </div>
          </div>

          <div className="admin-style-header-actions">
            <button
              className="admin-style-icon-button"
              onClick={() => {
                setSelectedMenu("notifications");
                loadParentNotifications();
              }}
              title="Notifications"
            >
              🔔
              {unreadNotificationCount > 0 && (
                <span className="notification-dot"></span>
              )}
            </button>

            <button
              className="admin-style-user-button parent-user-button"
              onClick={() => setSelectedMenu("my-profile")}
              title="Profile"
            >
              <span className="header-avatar">P</span>
              <span className="header-role-text">Parent</span>
              <span className="header-chevron">⌄</span>
            </button>
          </div>
        </header>

        <div className="admin-style-workspace">

          <section className="admin-style-map-panel">
            <div className="admin-style-map-title">
              <span className="admin-style-map-title-icon">📍</span>
              <div>
                <strong>Live Bus Tracking</strong>
                <small>Track your child's bus in real time</small>
              </div>
            </div>

            <MapContainer
              center={parentMapView.center}
              zoom={parentMapView.zoom}
              zoomControl={true}
              attributionControl={true}
              className="admin-style-map"
            >
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <PersistentMapView
                storageKey="smart-student-parent-map-view"
              />

              <Marker
                position={[
                  17.289612892928957,
                  76.86886054620065,
                ]}
              >
                <Popup>
                  <strong>🏫 Shetty Institute of Technology</strong>
                  <br />
                  School
                </Popup>
              </Marker>

              {busLocation && (
                <Marker
                  position={[
                    busLocation.latitude,
                    busLocation.longitude,
                  ]}
                >
                  <Popup>
                    <strong>🚌 BUS001</strong>
                    <br />
                    Mahantesh's school bus
                    <br />
                    Live location
                    <br />
                    <small>Updated: {busLocation.recorded_at}</small>
                  </Popup>
                </Marker>
              )}
            </MapContainer>

            <div className="admin-style-floating-bus">
              <div className="admin-style-bus-icon">🚌</div>
              <div>
                <strong>BUS001</strong>
                <span>{busLocationStatus}</span>
              </div>
              <span className={busLocation ? "live-pill live" : "live-pill"}>
                {busLocation ? "LIVE" : "OFF"}
              </span>
            </div>
          </section>

          <aside className="admin-style-dashboard-panel">
            <div className="admin-style-panel-heading">
              <div className="admin-style-panel-icon">🚌</div>
              <div>
                <p>SMART STUDENT BUS</p>
                <h2>Parent Dashboard</h2>
              </div>
            </div>

            <div className="admin-style-welcome">
              <p>WELCOME</p>
              <h2>Welcome, Parent 👋</h2>
              <span>Track your child and stay updated.</span>
            </div>

            <div className="admin-style-child-card">
              <div className="admin-style-child-avatar">👨‍🎓</div>
              <div>
                <strong>Mahantesh</strong>
                <span>STU001</span>
              </div>
              <span
                className={
                  travelStatus === "COMING"
                    ? "dashboard-status coming"
                    : travelStatus === "NOT_COMING"
                      ? "dashboard-status not-coming"
                      : "dashboard-status"
                }
              >
                ● {travelStatus === "COMING"
                  ? "COMING"
                  : travelStatus === "NOT_COMING"
                    ? "NOT COMING"
                    : "NO STATUS"}
              </span>
            </div>

            <div className="admin-style-detail-list">

              <div className="admin-style-detail-card">
                <span>📅</span>
                <div>
                  <strong>Today's Status</strong>
                  <small>
                    {travelStatus === "COMING"
                      ? "Coming"
                      : travelStatus === "NOT_COMING"
                        ? "Not Coming"
                        : "Not selected"}
                  </small>
                  <div className="admin-style-status-actions">
                    <button
                      className={travelStatus === "COMING" ? "selected" : ""}
                      onClick={() => updateTravelStatus("COMING")}
                      disabled={travelStatusLoading}
                    >
                      🚌 Coming
                    </button>
                    <button
                      className={travelStatus === "NOT_COMING" ? "selected" : ""}
                      onClick={() => updateTravelStatus("NOT_COMING")}
                      disabled={travelStatusLoading}
                    >
                      🚫 Not Coming
                    </button>
                  </div>
                </div>
              </div>

              <div className="admin-style-detail-card">
                <span>📍</span>
                <div>
                  <strong>Pickup Time</strong>
                  <small>07:45 AM</small>
                </div>
              </div>

              <div className="admin-style-detail-card">
                <span>📍</span>
                <div>
                  <strong>Drop Time</strong>
                  <small>03:30 PM</small>
                </div>
              </div>

              <div
                className="admin-style-detail-card admin-style-clickable"
                onClick={() => {
                  setSelectedMenu("calendar");
                  loadAttendanceHistory();
                }}
              >
                <span>☑</span>
                <div>
                  <strong>Attendance</strong>
                  <small>View attendance history</small>
                </div>
              </div>

            </div>

            <p className="admin-style-quick-title">QUICK ACCESS</p>

            <div className="admin-style-quick-list">
              <button onClick={() => setSelectedMenu("bus-schedule")}>
                <span>🚌</span>
                <strong>Bus Schedule</strong>
                <b>›</b>
              </button>

              <button
                onClick={() => {
                  setSelectedMenu("calendar");
                  loadAttendanceHistory();
                }}
              >
                <span>📅</span>
                <strong>Attendance Calendar</strong>
                <b>›</b>
              </button>

              <button
                onClick={() => {
                  setSelectedMenu("notifications");
                  loadParentNotifications();
                }}
              >
                <span>🔔</span>
                <strong>Notifications</strong>
                <b>›</b>
              </button>

              <button onClick={() => setSelectedMenu("my-profile")}>
                <span>👤</span>
                <strong>My Profile</strong>
                <b>›</b>
              </button>
            </div>
          </aside>

        </div>

        <nav className="admin-style-bottom-nav">
          <button
            className={!selectedMenu ? "active" : ""}
            onClick={() => setSelectedMenu(null)}
          >
            <span>🏠</span>
            <small>Home</small>
          </button>

          <button
            className={selectedMenu === "bus-schedule" ? "active" : ""}
            onClick={() => setSelectedMenu("bus-schedule")}
          >
            <span>🚌</span>
            <small>Bus</small>
          </button>

          <button
            className={selectedMenu === "calendar" ? "active" : ""}
            onClick={() => {
              setSelectedMenu("calendar");
              loadAttendanceHistory();
            }}
          >
            <span>📅</span>
            <small>Calendar</small>
          </button>

          <button
            className={selectedMenu === "notifications" ? "active" : ""}
            onClick={() => {
              setSelectedMenu("notifications");
              loadParentNotifications();
            }}
          >
            <span>🔔</span>
            <small>Notifications</small>
          </button>

          <button
            className={selectedMenu === "my-profile" ? "active" : ""}
            onClick={() => setSelectedMenu("my-profile")}
          >
            <span>👤</span>
            <small>Profile</small>
          </button>
        </nav>

        {selectedMenu && (

          <div className="map-menu-panel">

            <button
              className="map-menu-close"
              onClick={() => {

                setSelectedMenu(null);

              }}
            >
              ×
            </button>


            {selectedMenu ===
              "bus-schedule" && (

              <>

                <h2>
                  🚌 Bus Information
                </h2>


                <p>
                  Bus: <strong>BUS001</strong>
                </p>


                <p>
                  Driver:
                  {" "}
                  <strong>
                    Ramesh Kumar
                  </strong>
                </p>


                <p>
                  Route:
                  {" "}
                  <strong>
                    Main School Route
                  </strong>
                </p>


                <p>
                  Status:
                  {" "}
                  <strong>
                    Active
                  </strong>
                </p>

              </>

            )}


            {selectedMenu ===
              "calendar" && (

              <>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "8px",
                    marginBottom: "12px",
                  }}
                >

                  <button
                    onClick={goToPreviousMonth}
                    style={{
                      border: "none",
                      background: "#f5f7fa",
                      borderRadius: "8px",
                      padding: "8px 12px",
                      cursor: "pointer",
                    }}
                  >
                    ←
                  </button>

                  <div
                    style={{
                      textAlign: "center",
                      flex: 1,
                    }}
                  >
                    <h2 style={{ margin: 0 }}>
                      📅 Attendance Calendar
                    </h2>

                    <strong>
                      {calendarMonth.toLocaleString(
                        "default",
                        {
                          month: "long",
                          year: "numeric",
                        }
                      )}
                    </strong>
                  </div>

                  <button
                    onClick={goToNextMonth}
                    style={{
                      border: "none",
                      background: "#f5f7fa",
                      borderRadius: "8px",
                      padding: "8px 12px",
                      cursor: "pointer",
                    }}
                  >
                    →
                  </button>

                </div>


                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    marginBottom: "14px",
                  }}
                >

                  <button
                    onClick={goToCurrentMonth}
                    style={{
                      flex: 1,
                      padding: "8px",
                      border: "none",
                      borderRadius: "8px",
                      cursor: "pointer",
                    }}
                  >
                    Today
                  </button>

                  <button
                    onClick={loadAttendanceHistory}
                    disabled={attendanceHistoryLoading}
                    style={{
                      flex: 1,
                      padding: "8px",
                      border: "none",
                      borderRadius: "8px",
                      cursor: attendanceHistoryLoading
                        ? "not-allowed"
                        : "pointer",
                      opacity: attendanceHistoryLoading ? 0.6 : 1,
                    }}
                  >
                    {attendanceHistoryLoading
                      ? "Refreshing..."
                      : "↻ Refresh"}
                  </button>

                </div>


                {attendanceHistoryLoading ? (

                  <p>
                    Loading attendance...
                  </p>

                ) : (

                  <>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(7, 1fr)",
                        gap: "4px",
                        textAlign: "center",
                      }}
                    >

                      {[
                        "Sun",
                        "Mon",
                        "Tue",
                        "Wed",
                        "Thu",
                        "Fri",
                        "Sat",
                      ].map((day) => (

                        <strong
                          key={day}
                          style={{
                            fontSize: "12px",
                            padding: "6px 0",
                          }}
                        >
                          {day}
                        </strong>

                      ))}


                      {getCalendarDays().map(
                        (day, index) => {

                          if (!day) {

                            return (
                              <div
                                key={`empty-${index}`}
                                style={{
                                  minHeight: "48px",
                                }}
                              />
                            );

                          }


                          const year =
                            calendarMonth.getFullYear();

                          const month =
                            calendarMonth.getMonth();

                          const dateKey =
                            formatCalendarDate(
                              year,
                              month,
                              day
                            );

                          const attendanceDates =
                            getAttendanceDateSet();

                          const came =
                            attendanceDates.has(
                              dateKey
                            );


                          return (

                            <div
                              key={dateKey}
                              style={{
                                minHeight: "48px",
                                borderRadius: "8px",
                                padding: "5px 2px",
                                boxSizing: "border-box",
                                background: came
                                  ? "#e8f7ed"
                                  : "#f5f7fa",
                                border: came
                                  ? "1px solid #8fd19e"
                                  : "1px solid #e5e7eb",
                              }}
                            >

                              <div
                                style={{
                                  fontSize: "13px",
                                  fontWeight: "600",
                                }}
                              >
                                {day}
                              </div>

                              <div
                                style={{
                                  fontSize: "11px",
                                  marginTop: "3px",
                                }}
                              >
                                {came
                                  ? "🟢 Came to Bus"
                                  : "⚪ No record"}
                              </div>

                            </div>

                          );

                        }
                      )}

                    </div>


                    <div
                      style={{
                        marginTop: "14px",
                        fontSize: "13px",
                      }}
                    >
                      <div>🟢 Came to Bus</div>
                      <div>⚪ No attendance record</div>
                    </div>

                  </>

                )}

              </>

            )}


            {selectedMenu ===
              "notifications" && (

              <>

                <h2>
                  🔔 Notifications
                </h2>


                {notificationsLoading && (

                  <p>
                    Loading notifications...
                  </p>

                )}


                {!notificationsLoading &&
                  notifications.length === 0 && (

                  <p>
                    No notifications yet.
                  </p>

                )}


                {!notificationsLoading &&
                  notifications.map(
                    (notification) => (

                      <div
                        key={
                          notification.id
                        }
                        className="parent-notification-item"
                      >

                        <strong>
                          {notification.title}
                        </strong>


                        <p>
                          {notification.message}
                        </p>


                        <small>
                          {notification.created_at}
                        </small>


                        {!notification.is_read && (

                          <button
                            className="notification-read-button"
                            onClick={() =>
                              markNotificationRead(
                                notification.id
                              )
                            }
                          >
                            Mark as read
                          </button>

                        )}

                      </div>

                    )
                  )}

              </>

            )}


            {selectedMenu ===
              "my-profile" && (

              <>

                <h2>
                  👤 My Profile
                </h2>


                <p>
                  Parent account
                </p>


                <p>
                  Student:
                  {" "}
                  <strong>
                    Mahantesh
                  </strong>
                </p>


                <p>
                  Student ID:
                  {" "}
                  <strong>
                    STU001
                  </strong>
                </p>


                <button
                  className="map-logout-button"
                  onClick={logout}
                >
                  Logout
                </button>

              </>

            )}

          </div>

        )}


      </main>
    );

  }


  // ============================================================
  // DRIVER DASHBOARD
  // ============================================================

  if (
    selectedRole ===
    "DRIVER_HOME"
  ) {

    return (
      <main className="driver-admin-dashboard">

        <header className="admin-style-header">
          <div className="admin-style-brand">
            <div className="admin-style-logo">🚌</div>
            <div>
              <p>Smart Student Bus</p>
              <h1>Driver</h1>
            </div>
          </div>

          <div className="admin-style-header-actions">
            <button
              className="admin-style-icon-button"
              onClick={() => setSelectedMenu("alerts")}
              title="Alerts"
            >
              🔔
            </button>

            <button
              className="admin-style-user-button driver-user-button"
              onClick={() => setSelectedMenu("my-profile")}
              title="Profile"
            >
              <span className="header-avatar">D</span>
              <span className="header-role-text">Driver</span>
              <span className="header-chevron">⌄</span>
            </button>
          </div>
        </header>

        <div className="admin-style-workspace">

          <section className="admin-style-map-panel">
            <div className="admin-style-map-title">
              <span className="admin-style-map-title-icon">📍</span>
              <div>
                <strong>Live Bus Location</strong>
                <small>Your current location in real time</small>
              </div>
            </div>

            <div className="admin-style-driver-map">
              {driverLocation ? (
                <MapContainer
                  center={[
                    driverLocation.latitude,
                    driverLocation.longitude,
                  ]}
                  zoom={16}
                  className="admin-style-map"
                >
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  <LiveLocationView location={driverLocation} />

                  <Marker
                    position={[
                      driverLocation.latitude,
                      driverLocation.longitude,
                    ]}
                  >
                    <Popup>
                      <strong>🚌 BUS001</strong>
                      <br />
                      Live driver location
                      <br />
                      Accuracy: ±{Math.round(driverLocation.accuracy)} m
                    </Popup>
                  </Marker>
                </MapContainer>
              ) : (
                <div className="admin-style-map-empty">
                  <div>📍</div>
                  <strong>Waiting for live device location</strong>
                  <p>Start the trip to begin live tracking.</p>
                </div>
              )}
            </div>

            <div className="admin-style-floating-bus">
              <div className="admin-style-bus-icon">🚌</div>
              <div>
                <strong>BUS001</strong>
                <span>{gpsStatus}</span>
              </div>
              <span className={tripStatus === "IN_PROGRESS" ? "live-pill live" : "live-pill"}>
                {tripStatus === "IN_PROGRESS" ? "LIVE" : "WAITING"}
              </span>
            </div>
          </section>

          <aside className="admin-style-dashboard-panel">

            <div className="admin-style-panel-heading">
              <div className="admin-style-panel-icon">🚌</div>
              <div>
                <p>SMART STUDENT BUS</p>
                <h2>Driver Dashboard</h2>
              </div>
            </div>

            <div className="admin-style-welcome">
              <p>DRIVER</p>
              <h2>Good morning, Driver 👋</h2>
              <span>Manage your trip and students.</span>
            </div>

            <div className="admin-style-child-card driver-bus-summary">
              <div className="admin-style-child-avatar">🚌</div>
              <div>
                <strong>BUS001</strong>
                <span>Main School Route</span>
                <small>Driver: Ramesh Kumar</small>
              </div>
              <span className="dashboard-status coming">● ASSIGNED</span>
            </div>

            <div className="admin-style-trip-buttons">
              {tripStatus !== "IN_PROGRESS" ? (
                <button className="start-trip" onClick={startTrip}>
                  ▶ Start Trip
                </button>
              ) : (
                <button className="stop-trip" onClick={stopTrip}>
                  ■ Stop Trip
                </button>
              )}
            </div>

            <p className="admin-style-quick-title">TODAY'S STUDENTS</p>

            <div className="admin-style-student-counts">
              <div>
                <span>🟢</span>
                <strong>{travelSummary.coming}</strong>
                <small>Coming</small>
              </div>
              <div>
                <span>🔴</span>
                <strong>{travelSummary.notComing}</strong>
                <small>Not Coming</small>
              </div>
              <div>
                <span>⚪</span>
                <strong>{travelSummary.noStatus}</strong>
                <small>No Status</small>
              </div>
            </div>

            <p className="admin-style-quick-title">QUICK ACCESS</p>

            <div className="admin-style-quick-list">
              <button onClick={() => setSelectedMenu("students")}>
                <span>👥</span>
                <strong>Student Attendance</strong>
                <b>›</b>
              </button>

              <button
                onClick={() =>
                  document.querySelector(".driver-face-card")?.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                  })
                }
              >
                <span>📷</span>
                <strong>Face Recognition</strong>
                <b>›</b>
              </button>

              <button
                onClick={() =>
                  document.querySelector(".driver-gps-card")?.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                  })
                }
              >
                <span>📍</span>
                <strong>GPS / Alerts</strong>
                <b>›</b>
              </button>

              <button onClick={() => setSelectedMenu("my-profile")}>
                <span>👤</span>
                <strong>My Profile</strong>
                <b>›</b>
              </button>
            </div>

            <div className="admin-style-driver-students">
              <p className="section-label">Today's Students</p>

              {travelStudentsLoading && (
                <p className="detection-status">
                  Loading student travel status...
                </p>
              )}

              {!travelStudentsLoading &&
                todayTravelStudents.map((student) => (
                  <div
                    key={student.student_id}
                    className="attendance-row"
                  >
                    <div className="attendance-item">
                      <span className="attendance-icon">👨‍🎓</span>
                      <div>
                        <strong>{student.student_name}</strong>
                        <p>{student.student_code}</p>
                      </div>
                    </div>

                    <span
                      className={
                        student.status === "COMING"
                          ? "attendance-badge present"
                          : "attendance-badge pending"
                      }
                    >
                      {student.status === "COMING"
                        ? "🟢 COMING"
                        : student.status === "NOT_COMING"
                          ? "🔴 NOT COMING"
                          : "⚪ NO STATUS"}
                    </span>
                  </div>
                ))}
            </div>

            <div className="admin-style-hidden-details">
              <section className="travel-status-card driver-trip-card">
                <div>
                  <p className="section-label">Today's Trip</p>
                  <h2>Morning Pickup Trip</h2>
                  <p>
                    Trip ID: <strong>{tripId || "Not started"}</strong>
                  </p>
                  <p>
                    Status: <strong>{tripStatus}</strong>
                  </p>
                </div>
              </section>

        {/* CAMERA + RECOGNITION */}

        <section className="attendance-card driver-face-card">

          <p className="section-label">
            Face Recognition
          </p>


          <div className="camera-container">

            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="camera-video"
            />


            {!cameraActive && (

              <div className="camera-overlay">

                <span className="camera-large-icon">
                  📷
                </span>


                <p>
                  Laptop camera is ready
                </p>

              </div>

            )}


            {cameraActive &&
              detectedFaces.map(
                (face, index) => {

                  const video =
                    videoRef.current;


                  if (
                    !video ||
                    !video.videoWidth ||
                    !video.videoHeight
                  ) {

                    return null;

                  }


                  const recognizedFace =
                    recognizedFaces[index];


                  const label =
                    recognizedFace &&
                    recognizedFace.recognized
                      ? `✓ ${recognizedFace.name}`
                      : "Face detected";


                  return (

                    <div
                      key={index}
                      className="face-box"
                      style={{

                        left:
                          `${(
                            face.x /
                            video.videoWidth
                          ) * 100}%`,

                        top:
                          `${(
                            face.y /
                            video.videoHeight
                          ) * 100}%`,

                        width:
                          `${(
                            face.width /
                            video.videoWidth
                          ) * 100}%`,

                        height:
                          `${(
                            face.height /
                            video.videoHeight
                          ) * 100}%`,

                      }}
                    >

                      <span className="face-label">
                        {label}
                      </span>

                    </div>

                  );

                }
              )}

          </div>


          <button
            className="camera-button"
            onClick={
              cameraActive
                ? stopCamera
                : startCamera
            }
          >

            {cameraActive
              ? "⏹ Stop Camera"
              : "📷 Start Camera"}

          </button>


          {cameraActive && (

            <p className="detection-status">

              {detecting
                ? `🔍 Detecting faces... (${detectedFaces.length} found)`
                : "Camera ready"}

            </p>

          )}


          {recognizedFaces.length >
            0 && (

            <div>

              {recognizedFaces.map(
                (face, index) => (

                  <p
                    key={index}
                    className="detection-status"
                  >

                    {face.recognized
                      ? `✓ ${face.name} (${face.student_code})`
                      : "⚠ Unknown student"}

                  </p>

                )
              )}

            </div>

          )}


          {attendanceMessage && (

            <p className="detection-status">

              ✓ {attendanceMessage}

            </p>

          )}

        </section>


        {/* ATTENDANCE */}

        <section className="attendance-card driver-attendance-card">

          <p className="section-label">
            Attendance
          </p>


          <div className="attendance-row">

            <div className="attendance-item">

              <span className="attendance-icon">
                👤
              </span>


              <div>

                <strong>
                  Student Recognition
                </strong>


                <p>

                  {recognizedFaces.length === 0

                    ? "Waiting for a student..."

                    : recognizedFaces
                        .map(
                          (face) =>
                            face.recognized
                              ? `${face.name} (${face.student_code})`
                              : "Unknown student"
                        )
                        .join(", ")}

                </p>

              </div>

            </div>


            <span
              className={
                recognizedFaces.some(
                  (face) =>
                    face.recognized
                )
                  ? "attendance-badge present"
                  : "attendance-badge pending"
              }
            >

              {recognizedFaces.some(
                (face) =>
                  face.recognized
              )
                ? "Recognized"
                : "Waiting"}

            </span>

          </div>

        </section>


        {/* GPS */}

        <section className="attendance-card driver-gps-card">

          <p className="section-label">
            Location Tracking
          </p>


          <div className="attendance-row">

            <div className="attendance-item">

              <span className="attendance-icon">
                📍
              </span>


              <div>

                <strong>
                  Driver GPS
                </strong>


                <p>
                  {gpsStatus}
                </p>


                {driverLocation && (

                  <p>

                    Latitude:
                    {" "}
                    {driverLocation.latitude.toFixed(6)}

                    <br />

                    Longitude:
                    {" "}
                    {driverLocation.longitude.toFixed(6)}

                    <br />

                    Speed:
                    {" "}
                    {driverLocation.speed !== null
                      ? `${driverLocation.speed.toFixed(1)} km/h`
                      : "Unavailable"}

                    <br />

                    Accuracy:
                    {" "}
                    ±{Math.round(driverLocation.accuracy)} m

                  </p>

                )}

              </div>

            </div>


            <span
              className={
                gpsStatus.startsWith("GPS LIVE")
                  ? "attendance-badge present"
                  : "attendance-badge pending"
              }
            >
              {gpsStatus.startsWith("GPS LIVE")
                ? "LIVE"
                : "Waiting"}
            </span>

          </div>


          <p className="detection-status">

            {tripStatus ===
            "IN_PROGRESS"
              ? "Live device location is tracked automatically while the trip is active."
              : "Start a trip to begin live driver-location tracking."}

          </p>

        </section>



            </div>

          </aside>
        </div>

        <nav className="admin-style-bottom-nav">
          <button
            className={!selectedMenu ? "active" : ""}
            onClick={() => setSelectedMenu(null)}
          >
            <span>🏠</span>
            <small>Home</small>
          </button>

          <button
            className={selectedMenu === "students" ? "active" : ""}
            onClick={() => setSelectedMenu("students")}
          >
            <span>👥</span>
            <small>Students</small>
          </button>

          <button
            className="admin-nav-scroll"
            onClick={() =>
              document.querySelector(".driver-trip-card")?.scrollIntoView({
                behavior: "smooth",
                block: "center",
              })
            }
          >
            <span>🚌</span>
            <small>Trip</small>
          </button>

          <button
            className="admin-nav-scroll"
            onClick={() =>
              document.querySelector(".driver-gps-card")?.scrollIntoView({
                behavior: "smooth",
                block: "center",
              })
            }
          >
            <span>📍</span>
            <small>GPS</small>
          </button>

          <button
            className={selectedMenu === "my-profile" ? "active" : ""}
            onClick={() => setSelectedMenu("my-profile")}
          >
            <span>👤</span>
            <small>Profile</small>
          </button>
        </nav>

      </main>
    );

  }


  // ============================================================
  // ADMIN DASHBOARD
  // ============================================================


  const adminMapView = getSavedMapView(
    "smart-student-admin-map-view",
    [17.289612892928957, 76.86886054620065],
    15
  );

  if (
    selectedRole ===
    "ADMIN_HOME"
  ) {

    return (

      <main className={`parent-home admin-reference-dashboard admin-clean-shell ${selectedMenu ? "admin-has-menu" : ""}`}>

        <header className="parent-header admin-reference-header">

          <div className="admin-reference-brand">
            <div className="admin-reference-logo">🚌</div>

            <div>
              <p className="admin-reference-brand-name">
                Smart Student Bus
              </p>

              <h1>
                Admin
              </h1>
            </div>
          </div>

          <div className="admin-reference-header-actions">

            <button
              className="admin-reference-notification"
              onClick={() => setSelectedMenu("notifications")}
              title="Notifications"
            >
              🔔
            </button>

            <button
              className="admin-reference-profile"
              onClick={() => setSelectedMenu("my-profile")}
              title="Profile"
            >
              <span className="admin-reference-avatar">
                A
              </span>

              <span>
                Admin
              </span>

              <span className="admin-reference-chevron">
                ⌄
              </span>
            </button>

          </div>

        </header>


        <aside className="admin-sidebar">

          {/* BRAND */}
          <div className="admin-sidebar-brand">

            <div className="admin-sidebar-logo">
              🚌
            </div>

            <div>
              <strong>Smart Student Bus</strong>
              <span>Administration</span>
            </div>

          </div>


          {/* WORKSPACE */}
          <div className="admin-sidebar-section">

            <p className="admin-sidebar-label">
              WORKSPACE
            </p>


            <button
              className={
                !selectedMenu
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu(null)}
            >
              <span>🏠</span>
              <span>Dashboard</span>
            </button>


            <button
              className={
                selectedMenu === "students" ||
                selectedMenu === "student-management"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("students")}
            >
              <span>👨‍🎓</span>
              <span>Students</span>
            </button>


            <button
              className={
                selectedMenu === "buses"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("buses")}
            >
              <span>🚌</span>
              <span>Buses</span>
            </button>


            <button
              className={
                selectedMenu === "drivers"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("drivers")}
            >
              <span>👨‍✈️</span>
              <span>Drivers</span>
            </button>


            <button
              className={
                selectedMenu === "parents"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("parents")}
            >
              <span>👨‍👩‍👧</span>
              <span>Parents</span>
            </button>


            <button
              className={
                selectedMenu === "stop-management"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("stop-management")}
            >
              <span>🗺️</span>
              <span>Routes & Stops</span>
            </button>


            <button
              className={
                selectedMenu === "live-bus-location"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("live-bus-location")}
            >
              <span>📍</span>
              <span>Live Bus Tracking</span>
            </button>


            <button
              className={
                selectedMenu === "attendance"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("attendance")}
            >
              <span>📊</span>
              <span>Attendance</span>
            </button>

          </div>


          {/* COMMUNICATION */}
          <div className="admin-sidebar-section">

            <p className="admin-sidebar-label">
              COMMUNICATION
            </p>


            <button
              className={
                selectedMenu === "notifications"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("notifications")}
            >
              <span>🔔</span>
              <span>Notifications</span>
            </button>


            <button
              className={
                selectedMenu === "announcements"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("announcements")}
            >
              <span>📢</span>
              <span>Announcements</span>
            </button>

          </div>


          {/* SYSTEM */}
          <div className="admin-sidebar-section">

            <p className="admin-sidebar-label">
              SYSTEM
            </p>


            <button
              className={
                selectedMenu === "settings"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("settings")}
            >
              <span>⚙️</span>
              <span>Settings</span>
            </button>


            <button
              className={
                selectedMenu === "my-profile"
                  ? "admin-sidebar-item active"
                  : "admin-sidebar-item"
              }
              onClick={() => setSelectedMenu("my-profile")}
            >
              <span>👤</span>
              <span>My Profile</span>
            </button>

          </div>


          {/* LOGOUT */}
          <div className="admin-sidebar-bottom">

            <button
              className="admin-sidebar-item admin-logout-item"
              onClick={logout}
            >
              <span>🚪</span>
              <span>Logout</span>
            </button>

          </div>

        </aside>


        <div className="admin-clean-content">


        {selectedMenu === "stop-management" && (

          <section className="attendance-card">

            <StopManagement
              routes={routes}
              token={localStorage.getItem("token")}
            />

          </section>

        )}


        {(selectedMenu === "student-management" ||
          selectedMenu === "students") && (

          <section className="attendance-card">

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >

              <div>

                <p className="section-label">
                  Student Management
                </p>

                <h2>
                  Manage Students
                </h2>

                <p>
                  Add students, create family accounts,
                  and register student faces.
                </p>

              </div>


              <button
                className="camera-button"
                onClick={() => {

                  resetStudentForm();

                  setStudentFormOpen(true);

                  setFaceRegistrationOpen(false);

                }}
              >
                + Add Student
              </button>

            </div>


            {studentCreateMessage && (

              <p className="detection-status">
                {studentCreateMessage}
              </p>

            )}


            {createdParentCredentials && (

              <div
                style={{
                  marginTop: "14px",
                  padding: "14px",
                  borderRadius: "12px",
                  background: "#eef7ff",
                  border: "1px solid #cfe5ff",
                }}
              >

                <strong>
                  Family account created
                </strong>

                <p style={{ margin: "8px 0 4px" }}>
                  Parent ID:
                  {" "}
                  <strong>
                    {createdParentCredentials.username}
                  </strong>
                </p>

                {(createdParentCredentials.password ||
                  createdParentCredentials.temporary_password) && (

                  <p style={{ margin: "4px 0" }}>
                    Parent Password:
                    {" "}
                    <strong>
                      {createdParentCredentials.password ||
                        createdParentCredentials.temporary_password}
                    </strong>
                  </p>

                )}

                <small>
                  Save these credentials and provide them
                  to the family. The password is shown here only
                  after it is created or changed by the Admin.
                </small>

              </div>

            )}


            {studentFormOpen && (

              <form
                onSubmit={createStudent}
                style={{
                  marginTop: "18px",
                  padding: "16px",
                  borderRadius: "14px",
                  background: "#f7f9fc",
                  border: "1px solid #e4e8ef",
                }}
              >

                <h3>
                  Add Student
                </h3>

                <p>
                  Enter the parent details and create a password for the parent account.
                  If an existing Parent ID is used, the password will be changed for that account.
                </p>


                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "12px",
                  }}
                >

                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Student Name

                    <input
                      type="text"
                      value={studentForm.name}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            name: event.target.value,
                          })
                        )
                      }
                      placeholder="Enter student name"
                      required
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Class

                    <input
                      type="text"
                      value={studentForm.class_name}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            class_name: event.target.value,
                          })
                        )
                      }
                      placeholder="Example: 10-A"
                      required
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Father Name

                    <input
                      type="text"
                      value={studentForm.father_name}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            father_name: event.target.value,
                          })
                        )
                      }
                      placeholder="Optional"
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Mother Name

                    <input
                      type="text"
                      value={studentForm.mother_name}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            mother_name: event.target.value,
                          })
                        )
                      }
                      placeholder="Optional"
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Existing Parent ID

                    <input
                      type="text"
                      value={studentForm.parent_username}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            parent_username: event.target.value,
                          })
                        )
                      }
                      placeholder="Example: parent00001 (optional)"
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Parent Password

                    <input
                      type="password"
                      value={studentForm.parent_password}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            parent_password: event.target.value,
                          })
                        )
                      }
                      placeholder="Create password (min 6 characters)"
                      minLength={6}
                      required
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Parent Phone

                    <input
                      type="text"
                      value={studentForm.phone}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            phone: event.target.value,
                          })
                        )
                      }
                      placeholder="Optional"
                    />

                  </label>


                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "6px",
                    }}
                  >
                    Parent Email

                    <input
                      type="email"
                      value={studentForm.email}
                      onChange={(event) =>
                        setStudentForm(
                          (previous) => ({
                            ...previous,
                            email: event.target.value,
                          })
                        )
                      }
                      placeholder="Optional"
                    />

                  </label>

                </div>


                <div
                  style={{
                    display: "flex",
                    gap: "10px",
                    marginTop: "16px",
                    flexWrap: "wrap",
                  }}
                >

                  <button
                    type="submit"
                    className="camera-button"
                    disabled={studentCreating}
                  >
                    {studentCreating
                      ? "Creating..."
                      : "Create Student"}
                  </button>


                  <button
                    type="button"
                    className="camera-button"
                    onClick={() => {

                      setStudentFormOpen(false);

                      resetStudentForm();

                    }}
                    disabled={studentCreating}
                  >
                    Cancel
                  </button>

                </div>

              </form>

            )}


            <div style={{ marginTop: "20px" }}>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(250px, 1fr))",
                  gap: "12px",
                }}
              >

                {studentsLoading && (

                  <p>
                    Loading students...
                  </p>

                )}


                {!studentsLoading &&
                  students.length === 0 && (

                  <p>
                    No students found.
                  </p>

                )}


                {!studentsLoading &&
                  students.map((student) => (

                    <div
                      key={student.id}
                      style={{
                        padding: "14px",
                        borderRadius: "14px",
                        border: "1px solid #e4e8ef",
                        background: "#fff",
                      }}
                    >

                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: "10px",
                        }}
                      >

                        <div>

                          <strong>
                            {student.name}
                          </strong>

                          <p style={{ margin: "4px 0" }}>
                            {student.student_code}
                            {" • "}
                            {student.class_name || "Class not assigned"}
                          </p>

                        </div>


                        <span
                          className={
                            student.has_face
                              ? "attendance-badge present"
                              : "attendance-badge pending"
                          }
                        >
                          {student.has_face
                            ? "✓ Face"
                            : "Face Pending"}
                        </span>

                      </div>


                      <p style={{ margin: "8px 0 4px" }}>
                        Father:
                        {" "}
                        {student.parent?.father_name ||
                          "Not provided"}
                      </p>


                      <p style={{ margin: "4px 0" }}>
                        Mother:
                        {" "}
                        {student.parent?.mother_name ||
                          "Not provided"}
                      </p>


                      <p style={{ margin: "4px 0" }}>
                        Parent ID:
                        {" "}
                        <strong>
                          {student.parent?.username ||
                            "Not assigned"}
                        </strong>
                      </p>


                      <p style={{ margin: "4px 0", color: "#64748b" }}>
                        Parent Password:
                        {" "}
                        <strong>
                          {student.parent?.password ||
                            "Hidden — create/reset from Admin"}
                        </strong>
                      </p>


                      <div className="student-card-actions">

                        <button
                          className="camera-button"
                          onClick={() =>
                            openFaceRegistration(student)
                          }
                        >
                          {student.has_face
                            ? "📷 Update Face"
                            : "📷 Register Face"}
                        </button>

                        <button
                          type="button"
                          className="student-delete-button"
                          onClick={() =>
                            deleteStudent(student)
                          }
                        >
                          🗑 Delete Student Permanently
                        </button>

                      </div>

                    </div>

                  ))}

              </div>

            </div>


            {faceRegistrationOpen &&
              selectedStudentId && (

              <div
                style={{
                  marginTop: "20px",
                  padding: "16px",
                  borderRadius: "14px",
                  border: "1px solid #dfe5ed",
                  background: "#f8fafc",
                }}
              >

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "10px",
                  }}
                >

                  <div>

                    <p className="section-label">
                      Face Registration
                    </p>

                    <h3>
                      {selectedStudentName}
                    </h3>

                    <p>
                      Student ID: {selectedStudentId}
                    </p>

                  </div>


                  <button
                    type="button"
                    className="camera-button"
                    onClick={closeFaceRegistration}
                  >
                    Close
                  </button>

                </div>


                <div className="camera-container">

                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="camera-video"
                  />


                  {!cameraActive && (

                    <div className="camera-overlay">

                      <span className="camera-large-icon">
                        📷
                      </span>

                      <p>
                        Start camera to register face
                      </p>

                    </div>

                  )}


                  {cameraActive &&
                    detectedFaces.map(
                      (face, index) => {

                        const video =
                          videoRef.current;

                        if (
                          !video ||
                          !video.videoWidth ||
                          !video.videoHeight
                        ) {

                          return null;

                        }

                        return (

                          <div
                            key={index}
                            className="face-box"
                            style={{
                              left:
                                `${(
                                  face.x /
                                  video.videoWidth
                                ) * 100}%`,

                              top:
                                `${(
                                  face.y /
                                  video.videoHeight
                                ) * 100}%`,

                              width:
                                `${(
                                  face.width /
                                  video.videoWidth
                                ) * 100}%`,

                              height:
                                `${(
                                  face.height /
                                  video.videoHeight
                                ) * 100}%`,
                            }}
                          >

                            <span className="face-label">
                              Face detected
                            </span>

                          </div>

                        );

                      }
                    )}

                </div>


                <button
                  className="camera-button"
                  onClick={
                    cameraActive
                      ? stopCamera
                      : startCamera
                  }
                >
                  {cameraActive
                    ? "⏹ Stop Camera"
                    : "📷 Start Camera"}
                </button>


                <button
                  className="camera-button"
                  onClick={registerStudentFace}
                  disabled={
                    registering ||
                    !cameraActive ||
                    detectedFaces.length !== 1
                  }
                >
                  {registering
                    ? "Registering..."
                    : "✓ Save Face"}
                </button>


                {registrationStatus && (

                  <p className="detection-status">
                    {registrationStatus}
                  </p>

                )}

              </div>

            )}

          </section>

        )}

        {/* ========================================================
           ADMIN DASHBOARD-ONLY CONTENT
           These sections are rendered ONLY when no Admin module
           is selected. Therefore the live dashboard map cannot
           appear on Students, Buses, Drivers, Parents, Attendance,
           Notifications, Settings, Profile, etc.
           Routes & Stops has its own map inside StopManagement.
           ======================================================== */}
        {selectedMenu === null && (
          <>

        {/* SYSTEM OVERVIEW */}

        <section className="bus-info-card admin-reference-summary-card admin-dashboard-only">

          <p className="section-label">
            System Overview
          </p>


          <div className="bus-info-grid">

            <div className="bus-info-item">

              <span className="bus-info-icon">
                👨‍🎓
              </span>


              <div>

                <span>
                  Students
                </span>


                <strong>
                  {students.length || 1}
                </strong>

              </div>

            </div>


            <div className="bus-info-item">

              <span className="bus-info-icon">
                🚌
              </span>


              <div>

                <span>
                  Buses
                </span>


                <strong>
                  1
                </strong>

              </div>

            </div>


            <div className="bus-info-item">

              <span className="bus-info-icon">
                👨‍✈️
              </span>


              <div>

                <span>
                  Drivers
                </span>


                <strong>
                  1
                </strong>

              </div>

            </div>


            <div className="bus-info-item">

              <span className="bus-info-icon">
                👨‍👩‍👧
              </span>


              <div>

                <span>
                  Parents
                </span>


                <strong>
                  2
                </strong>

              </div>

            </div>

          </div>

        </section>


        {/* LIVE BUS TRACKING */}

        <section className="map-card admin-reference-map-card admin-dashboard-only">

          <div
            style={{
              width: "100%",
              minHeight: "350px",
              position: "relative",
            }}
          >

            <MapContainer
              center={adminMapView.center}
              zoom={adminMapView.zoom}
              style={{
                width: "100%",
                height: "350px",
              }}
            >

              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <PersistentMapView
                storageKey="smart-student-admin-map-view"
              />

              <Marker
                position={[
                  17.289612892928957,
                  76.86886054620065,
                ]}
              >
                <Popup>
                  <strong>🏫 Shetty Institute of Technology</strong>
                  <br />
                  School
                </Popup>
              </Marker>

              {busLocation && (

                <>
                  <Marker
                    position={[
                      busLocation.latitude,
                      busLocation.longitude,
                    ]}
                  >

                    <Popup>

                      <strong>
                        🚌 BUS001
                      </strong>

                      <br />

                      Live bus location

                      <br />

                      Status:
                      {" "}
                      {busLocation.status}

                      <br />

                      Updated:
                      {" "}
                      {busLocation.recorded_at}

                    </Popup>

                  </Marker>
                </>

              )}

            </MapContainer>

          </div>


          <div
            style={{
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >

            <div>

              <strong>
                🚌 BUS001
              </strong>


              <p
                style={{
                  margin: "4px 0 0",
                }}
              >
                {busLocationStatus}
              </p>

            </div>


            <span
              className={
                busLocation
                  ? "attendance-badge present"
                  : "attendance-badge pending"
              }
            >
              {busLocation ? "LIVE" : "OFFLINE"}
            </span>

          </div>

        </section>


        {/* ADMIN ACTIONS */}

        <div className="parent-actions admin-reference-quick-access admin-dashboard-only">

          <button
            className="action-card"
            onClick={() => {

              setSelectedMenu(
                "student-management"
              );

              loadStudents();

            }}
          >

            <span>
              👨‍🎓
            </span>


            <div>

              <strong>
                Students
              </strong>


              <p>
                Manage students
              </p>

            </div>

          </button>


          <button className="action-card">

            <span>
              🚌
            </span>


            <div>

              <strong>
                Buses
              </strong>


              <p>
                Manage buses
              </p>

            </div>

          </button>


          <button className="action-card">

            <span>
              👨‍✈️
            </span>


            <div>

              <strong>
                Drivers
              </strong>


              <p>
                Manage drivers
              </p>

            </div>

          </button>


          <button className="action-card">

            <span>
              🗺️
            </span>


            <div>

              <strong>
                Routes & Stops
              </strong>


              <p>
                Manage routes and stops
              </p>

            </div>

          </button>


          <button className="action-card">

            <span>
              📊
            </span>


            <div>

              <strong>
                Attendance Reports
              </strong>


              <p>
                View attendance
              </p>

            </div>

          </button>


          <button className="action-card">

            <span>
              🔔
            </span>


            <div>

              <strong>
                Notifications
              </strong>


              <p>
                Manage notifications
              </p>

            </div>

          </button>

        </div>

          </>
        )}

      </div>


      </main>

    );

  }


  return null;

}


export default App;