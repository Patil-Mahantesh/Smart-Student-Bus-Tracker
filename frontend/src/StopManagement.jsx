/*
  StopManagement.jsx

  Map-based Stop Management for Admin.

  Requirements:
    npm install leaflet react-leaflet
*/

import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  Marker,
  TileLayer,
  useMapEvents,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";


// ------------------------------------------------------------
// Leaflet marker fix for Vite
// ------------------------------------------------------------

const markerIcon = L.icon({
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",

  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",

  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",

  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});


// ------------------------------------------------------------
// Default map center
// ------------------------------------------------------------

const DEFAULT_CENTER = [
  17.3297,
  76.8343,
];


// ------------------------------------------------------------
// Map click selector
// ------------------------------------------------------------

function LocationPicker({
  selectedLocation,
  onSelect,
}) {

  useMapEvents({
    click(event) {

      onSelect({
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      });

    },
  });

  if (!selectedLocation) {
    return null;
  }

  return (
    <Marker
      position={[
        selectedLocation.latitude,
        selectedLocation.longitude,
      ]}
      icon={markerIcon}
    />
  );
}


// ------------------------------------------------------------
// Recenter map when editing a stop
// ------------------------------------------------------------

function MapRecenter({
  location,
}) {

  const map = useMap();

  useEffect(() => {

    if (!location) {
      return;
    }

    map.setView(
      [
        location.latitude,
        location.longitude,
      ],
      Math.max(
        map.getZoom(),
        15
      )
    );

  }, [location, map]);

  return null;
}


// ============================================================
// STOP MANAGEMENT
// ============================================================

export default function StopManagement({
  routes = [],
  token,
}) {

  const [stops, setStops] =
    useState([]);

  const [selectedRouteId, setSelectedRouteId] =
    useState(
      routes.length
        ? routes[0].id
        : ""
    );

  const [stopName, setStopName] =
    useState("");

  const [stopType, setStopType] =
    useState("PICKUP");

  const [stopOrder, setStopOrder] =
    useState(1);

  const [location, setLocation] =
    useState(null);

  const [editingStopId, setEditingStopId] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [error, setError] =
    useState("");


  // ----------------------------------------------------------
  // Load stops
  // ----------------------------------------------------------

  const loadStops = async () => {

    if (!token) {
      return;
    }

    try {

      const response =
        await fetch(
          "http://localhost:5000/api/stops",
          {
            headers: {
              Authorization:
                `Bearer ${token}`,
            },
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.message ||
          "Unable to load stops."
        );
      }

      setStops(
        data.stops || []
      );

    } catch (loadError) {

      setError(
        loadError.message
      );

    }

  };


  useEffect(() => {
    loadStops();
  }, [token]);


  // ----------------------------------------------------------
  // Current route
  // ----------------------------------------------------------

  const currentRoute =
    useMemo(
      () =>
        routes.find(
          route =>
            String(route.id) ===
            String(selectedRouteId)
        ),
      [routes, selectedRouteId]
    );


  // ----------------------------------------------------------
  // Filter stops for selected route
  // ----------------------------------------------------------

  const routeStops =
    useMemo(
      () =>
        stops
          .filter(
            stop =>
              String(stop.route_id) ===
              String(selectedRouteId)
          )
          .sort(
            (a, b) =>
              Number(a.stop_order) -
              Number(b.stop_order)
          ),
      [stops, selectedRouteId]
    );


  // ----------------------------------------------------------
  // Reset form
  // ----------------------------------------------------------

  const resetForm = () => {

    setEditingStopId(null);
    setStopName("");
    setStopType("PICKUP");
    setStopOrder(
      routeStops.length + 1
    );
    setLocation(null);
    setError("");

  };


  // ----------------------------------------------------------
  // Start editing
  // ----------------------------------------------------------

  const editStop = (stop) => {

    setEditingStopId(
      stop.id
    );

    setSelectedRouteId(
      stop.route_id
    );

    setStopName(
      stop.stop_name
    );

    setStopType(
      stop.stop_type
    );

    setStopOrder(
      stop.stop_order
    );

    setLocation({
      latitude:
        Number(stop.latitude),
      longitude:
        Number(stop.longitude),
    });

    setMessage("");

    setError("");

  };


  // ----------------------------------------------------------
  // Save stop
  // ----------------------------------------------------------

  const saveStop = async () => {

    setMessage("");
    setError("");

    if (!selectedRouteId) {

      setError(
        "Please select a route."
      );

      return;
    }

    if (!stopName.trim()) {

      setError(
        "Please enter a stop name."
      );

      return;
    }

    if (!location) {

      setError(
        "Click a location on the map before saving."
      );

      return;
    }

    setLoading(true);

    try {

      const url =
        editingStopId
          ? `http://localhost:5000/api/stops/${editingStopId}`
          : "http://localhost:5000/api/stops";

      const response =
        await fetch(
          url,
          {
            method:
              editingStopId
                ? "PUT"
                : "POST",

            headers: {
              "Content-Type":
                "application/json",

              Authorization:
                `Bearer ${token}`,
            },

            body:
              JSON.stringify({
                route_id:
                  Number(selectedRouteId),

                stop_name:
                  stopName.trim(),

                stop_type:
                  stopType,

                latitude:
                  location.latitude,

                longitude:
                  location.longitude,

                stop_order:
                  Number(stopOrder),
              }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.message ||
          "Unable to save stop."
        );

      }

      setMessage(
        editingStopId
          ? "Stop updated successfully."
          : "Stop added successfully."
      );

      resetForm();

      await loadStops();

    } catch (saveError) {

      setError(
        saveError.message
      );

    } finally {

      setLoading(false);

    }

  };


  // ----------------------------------------------------------
  // Delete stop
  // ----------------------------------------------------------

  const deleteStop = async (stop) => {

    const confirmed =
      window.confirm(
        `Delete "${stop.stop_name}"?`
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setMessage("");

    try {

      const response =
        await fetch(
          `http://localhost:5000/api/stops/${stop.id}`,
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

        throw new Error(
          data.message ||
          "Unable to delete stop."
        );

      }

      setMessage(
        data.message ||
        "Stop deleted successfully."
      );

      if (
        editingStopId ===
        stop.id
      ) {
        resetForm();
      }

      await loadStops();

    } catch (deleteError) {

      setError(
        deleteError.message
      );

    }

  };


  // ----------------------------------------------------------
  // Render
  // ----------------------------------------------------------

  return (
    <div
      className="stop-management"
      style={{
        display: "grid",
        gridTemplateColumns:
          "360px minmax(0, 1fr)",
        gap: "16px",
        height: "100%",
        minHeight: "620px",
      }}
    >

      {/* =====================================================
          LEFT PANEL
          ===================================================== */}

      <section
        style={{
          background: "#fff",
          border: "1px solid #e4e9f1",
          borderRadius: "18px",
          padding: "18px",
          overflow: "auto",
          boxShadow:
            "0 8px 25px rgba(15,23,42,.05)",
        }}
      >

        <div
          style={{
            marginBottom: "18px",
          }}
        >

          <p
            style={{
              margin: 0,
              color: "#71809a",
              fontSize: "9px",
              fontWeight: 850,
              letterSpacing: ".8px",
            }}
          >
            ROUTE MANAGEMENT
          </p>

          <h2
            style={{
              margin:
                "5px 0 0",
              color: "#172033",
              fontSize: "20px",
              fontWeight: 850,
            }}
          >
            Manage Stops
          </h2>

        </div>


        {/* Route */}

        <label
          style={{
            display: "block",
            marginBottom: "6px",
            color: "#47566f",
            fontSize: "11px",
            fontWeight: 800,
          }}
        >
          Route
        </label>

        <select
          value={selectedRouteId}
          onChange={event => {

            setSelectedRouteId(
              event.target.value
            );

            resetForm();

          }}
          style={{
            width: "100%",
            minHeight: "43px",
            padding: "0 11px",
            border:
              "1px solid #dfe6ef",
            borderRadius: "10px",
            background: "#f8fafc",
            color: "#26344c",
            fontFamily: "inherit",
            fontSize: "12px",
            outline: "none",
          }}
        >

          <option value="">
            Select route
          </option>

          {routes.map(route => (

            <option
              key={route.id}
              value={route.id}
            >
              {route.route_name}
            </option>

          ))}

        </select>


        {/* Stop name */}

        <label
          style={{
            display: "block",
            margin:
              "14px 0 6px",
            color: "#47566f",
            fontSize: "11px",
            fontWeight: 800,
          }}
        >
          Stop Name
        </label>

        <input
          value={stopName}
          onChange={event =>
            setStopName(
              event.target.value
            )
          }
          placeholder="e.g. Gandhi Nagar"
          style={{
            width: "100%",
            minHeight: "43px",
            padding: "0 11px",
            boxSizing: "border-box",
            border:
              "1px solid #dfe6ef",
            borderRadius: "10px",
            background: "#f8fafc",
            color: "#26344c",
            fontFamily: "inherit",
            fontSize: "12px",
            outline: "none",
          }}
        />


        {/* Stop type */}

        <label
          style={{
            display: "block",
            margin:
              "14px 0 7px",
            color: "#47566f",
            fontSize: "11px",
            fontWeight: 800,
          }}
        >
          Stop Type
        </label>

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              "1fr 1fr",
            gap: "7px",
          }}
        >

          {["PICKUP", "DROP"].map(type => (

            <button
              key={type}
              type="button"
              onClick={() =>
                setStopType(type)
              }
              style={{
                minHeight: "40px",
                border:
                  stopType === type
                    ? "1px solid #bcd7ff"
                    : "1px solid #e1e7ef",
                borderRadius: "10px",
                background:
                  stopType === type
                    ? "#edf5ff"
                    : "#fff",
                color:
                  stopType === type
                    ? "#2563eb"
                    : "#687991",
                fontFamily: "inherit",
                fontSize: "10px",
                fontWeight: 850,
                cursor: "pointer",
              }}
            >
              {type === "PICKUP"
                ? "🟢 Pickup"
                : "🔴 Drop"}
            </button>

          ))}

        </div>


        {/* Order */}

        <label
          style={{
            display: "block",
            margin:
              "14px 0 6px",
            color: "#47566f",
            fontSize: "11px",
            fontWeight: 800,
          }}
        >
          Stop Order
        </label>

        <input
          type="number"
          min="1"
          value={stopOrder}
          onChange={event =>
            setStopOrder(
              event.target.value
            )
          }
          style={{
            width: "100%",
            minHeight: "43px",
            padding: "0 11px",
            boxSizing: "border-box",
            border:
              "1px solid #dfe6ef",
            borderRadius: "10px",
            background: "#f8fafc",
            color: "#26344c",
            fontFamily: "inherit",
            fontSize: "12px",
            outline: "none",
          }}
        />


        {/* Selected location */}

        <div
          style={{
            marginTop: "14px",
            padding: "11px",
            borderRadius: "11px",
            background:
              location
                ? "#edf8f1"
                : "#f7f9fc",
            border:
              location
                ? "1px solid #ccebd9"
                : "1px solid #e6ebf2",
          }}
        >

          <div
            style={{
              color: "#71809a",
              fontSize: "9px",
              fontWeight: 850,
              letterSpacing: ".5px",
            }}
          >
            SELECTED MAP LOCATION
          </div>

          {location ? (

            <div
              style={{
                marginTop: "5px",
                color: "#217447",
                fontSize: "11px",
                fontWeight: 800,
              }}
            >
              📍{" "}
              {location.latitude.toFixed(6)}
              {" , "}
              {location.longitude.toFixed(6)}
            </div>

          ) : (

            <div
              style={{
                marginTop: "5px",
                color: "#8a98ab",
                fontSize: "10px",
              }}
            >
              Click anywhere on the map.
            </div>

          )}

        </div>


        {/* Messages */}

        {message && (

          <div
            style={{
              marginTop: "10px",
              padding: "10px",
              borderRadius: "10px",
              background: "#edf8f1",
              color: "#187343",
              fontSize: "10px",
              fontWeight: 750,
            }}
          >
            ✓ {message}
          </div>

        )}

        {error && (

          <div
            style={{
              marginTop: "10px",
              padding: "10px",
              borderRadius: "10px",
              background: "#fff1f2",
              color: "#b42336",
              fontSize: "10px",
              fontWeight: 750,
            }}
          >
            {error}
          </div>

        )}


        {/* Save / Cancel */}

        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              editingStopId
                ? "1fr 1fr"
                : "1fr",
            gap: "7px",
            marginTop: "13px",
          }}
        >

          {editingStopId && (

            <button
              type="button"
              onClick={resetForm}
              style={{
                minHeight: "43px",
                border:
                  "1px solid #dfe6ef",
                borderRadius: "10px",
                background: "#fff",
                color: "#64748b",
                fontFamily: "inherit",
                fontSize: "10px",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>

          )}

          <button
            type="button"
            disabled={loading}
            onClick={saveStop}
            style={{
              minHeight: "43px",
              border: "0",
              borderRadius: "10px",
              background: "#2563eb",
              color: "#fff",
              fontFamily: "inherit",
              fontSize: "10px",
              fontWeight: 850,
              cursor:
                loading
                  ? "wait"
                  : "pointer",
              opacity:
                loading
                  ? .7
                  : 1,
            }}
          >
            {loading
              ? "Saving..."
              : editingStopId
                ? "Save Changes"
                : "📍 Save Stop"}
          </button>

        </div>


        {/* Existing stops */}

        <div
          style={{
            marginTop: "22px",
          }}
        >

          <p
            style={{
              margin:
                "0 0 8px",
              color: "#71809a",
              fontSize: "9px",
              fontWeight: 850,
              letterSpacing: ".8px",
            }}
          >
            STOPS ON THIS ROUTE
          </p>

          {routeStops.length === 0 ? (

            <div
              style={{
                padding: "16px",
                textAlign: "center",
                border:
                  "1px dashed #dce3ed",
                borderRadius: "11px",
                color: "#8996a9",
                fontSize: "10px",
              }}
            >
              No stops added yet.
            </div>

          ) : (

            <div
              style={{
                display: "grid",
                gap: "7px",
              }}
            >

              {routeStops.map(stop => (

                <div
                  key={stop.id}
                  style={{
                    padding: "10px",
                    border:
                      "1px solid #e5ebf3",
                    borderRadius: "11px",
                    background: "#f8fafc",
                  }}
                >

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >

                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        flex: "0 0 28px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                          "center",
                        borderRadius: "8px",
                        background:
                          stop.stop_type ===
                          "PICKUP"
                            ? "#e9f8ef"
                            : "#fff0f2",
                      }}
                    >
                      {stop.stop_type ===
                      "PICKUP"
                        ? "🟢"
                        : "🔴"}
                    </div>

                    <div
                      style={{
                        flex: 1,
                        minWidth: 0,
                      }}
                    >

                      <strong
                        style={{
                          display: "block",
                          color: "#27344b",
                          fontSize: "11px",
                          fontWeight: 850,
                        }}
                      >
                        {stop.stop_order}.{" "}
                        {stop.stop_name}
                      </strong>

                      <small
                        style={{
                          display: "block",
                          marginTop: "3px",
                          color: "#8592a6",
                          fontSize: "8px",
                        }}
                      >
                        {stop.stop_type}
                        {" • "}
                        {Number(
                          stop.latitude
                        ).toFixed(5)}
                        {", "}
                        {Number(
                          stop.longitude
                        ).toFixed(5)}
                      </small>

                    </div>

                  </div>


                  <div
                    style={{
                      display: "flex",
                      gap: "6px",
                      marginTop: "8px",
                    }}
                  >

                    <button
                      type="button"
                      onClick={() =>
                        editStop(stop)
                      }
                      style={{
                        flex: 1,
                        minHeight: "31px",
                        border:
                          "1px solid #dce6f2",
                        borderRadius: "8px",
                        background: "#fff",
                        color: "#315fd5",
                        fontFamily:
                          "inherit",
                        fontSize: "9px",
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      Edit
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        deleteStop(stop)
                      }
                      style={{
                        flex: 1,
                        minHeight: "31px",
                        border:
                          "1px solid #fecaca",
                        borderRadius: "8px",
                        background: "#fff1f2",
                        color: "#b42336",
                        fontFamily:
                          "inherit",
                        fontSize: "9px",
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      Delete
                    </button>

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>

      </section>


      {/* =====================================================
          RIGHT MAP
          ===================================================== */}

      <section
        style={{
          position: "relative",
          minWidth: 0,
          overflow: "hidden",
          borderRadius: "18px",
          border: "1px solid #e2e8f0",
          background: "#e9eef5",
          boxShadow:
            "0 8px 25px rgba(15,23,42,.05)",
        }}
      >

        <MapContainer
          center={DEFAULT_CENTER}
          zoom={14}
          scrollWheelZoom={true}
          style={{
            width: "100%",
            height: "100%",
            minHeight: "620px",
          }}
        >

          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapRecenter
            location={location}
          />

          <LocationPicker
            selectedLocation={location}
            onSelect={setLocation}
          />

          {routeStops.map(stop => (

            <Marker
              key={stop.id}
              position={[
                Number(stop.latitude),
                Number(stop.longitude),
              ]}
              icon={markerIcon}
              opacity={
                editingStopId === stop.id
                  ? 0.45
                  : 1
              }
            />

          ))}

        </MapContainer>


        {/* Map instruction */}

        <div
          style={{
            position: "absolute",
            zIndex: 1000,
            left: "14px",
            top: "14px",
            maxWidth: "290px",
            padding: "11px 14px",
            borderRadius: "12px",
            background:
              "rgba(255,255,255,.96)",
            border:
              "1px solid #e3e9f1",
            boxShadow:
              "0 8px 20px rgba(15,23,42,.10)",
          }}
        >

          <strong
            style={{
              display: "block",
              color: "#26344c",
              fontSize: "11px",
              fontWeight: 850,
            }}
          >
            📍 Click the map to select a stop
          </strong>

          <span
            style={{
              display: "block",
              marginTop: "3px",
              color: "#8492a7",
              fontSize: "9px",
            }}
          >
            {currentRoute
              ? currentRoute.route_name
              : "Select a route first"}
          </span>

        </div>

      </section>

    </div>
  );
}
