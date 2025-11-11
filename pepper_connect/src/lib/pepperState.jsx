// src/lib/pepperState.jsx

// ===== Config =====
const EMOTION_API_BASE =
  import.meta.env?.VITE_EMOTION_API_URL || "http://localhost:8000";

// IMPORTANTE: Audio y Face usan el mismo servidor para estado de Pepper
// Ambos sensores deben chequear el mismo endpoint de estado
const AUDIO_API_BASE =
  import.meta.env?.VITE_EMOTION_API_URL || "http://localhost:8000";

/**
 * Check if Pepper is available to receive new scripts (Face Detection)
 * @param {string} room - Optional room identifier
 * @returns {Promise<boolean>} true if Pepper is available (proce = 1)
 */
export async function isPepperAvailable(room = "test") {
  try {
    const url = `${EMOTION_API_BASE}/pepper/status${room ? `?room=${room}` : ''}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      console.warn(`Pepper status check failed: ${response.status} ${response.statusText}`);
      return true; // Default to available if check fails
    }

    const data = await response.json();
    return data.proce === 1; // 1 = available, 0 = busy

  } catch (error) {
    console.warn("Pepper status check error:", error.message);
    return true; // Default to available if check fails
  }
}

/**
 * Check if Pepper is available to receive new scripts (Audio Processing)
 * @param {string} room - Optional room identifier
 * @returns {Promise<boolean>} true if Pepper is available (proce = 1)
 */
export async function isPepperAvailableForAudio(room = "test") {
  try {
    const url = `${AUDIO_API_BASE}/pepper/status${room ? `?room=${room}` : ''}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      console.warn(`Pepper status check (audio) failed: ${response.status} ${response.statusText}`);
      return true; // Default to available if check fails
    }

    const data = await response.json();
    return data.proce === 1; // 1 = available, 0 = busy

  } catch (error) {
    console.warn("Pepper status check (audio) error:", error.message);
    return true; // Default to available if check fails
  }
}

/**
 * Check if Pepper is busy executing a script
 * @param {string} room - Optional room identifier
 * @returns {Promise<boolean>} true if Pepper is busy (proce = 0)
 */
export async function isPepperBusy(room = "test") {
  const available = await isPepperAvailable(room);
  return !available;
}

/**
 * Get full Pepper status information
 * @param {string} room - Optional room identifier
 * @returns {Promise<object>} Complete status object
 */
export async function getPepperStatus(room = "test") {
  try {
    const url = `${EMOTION_API_BASE}/pepper/status${room ? `?room=${room}` : ''}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();

  } catch (error) {
    console.error("Pepper status error:", error);
    return {
      proce: 1, // Default to available
      available: true,
      busy: false,
      error: error.message
    };
  }
}

/**
 * Set Pepper as available (proce=1) after animation completes
 * @param {string} room - Optional room identifier
 * @returns {Promise<boolean>} true if successful
 */
export async function setPepperAvailable(room = "test") {
  try {
    const formData = new FormData();
    if (room) formData.append('room', room);

    const response = await fetch(`${EMOTION_API_BASE}/pepper/set-available`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Set available failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log("✅ Pepper state set to AVAILABLE:", data.message);
    return data.success;

  } catch (error) {
    console.error("❌ Set Pepper available error:", error);
    return false;
  }
}

/**
 * Manually mark Pepper as available (emergency reset)
 * @param {string} room - Optional room identifier
 * @returns {Promise<boolean>} true if reset was successful
 */
export async function resetPepperState(room = "test") {
  try {
    const response = await fetch(`${EMOTION_API_BASE}/pepper/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`Reset failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Pepper state reset:", data.message);
    return data.success;

  } catch (error) {
    console.error("Pepper reset error:", error);
    return false;
  }
}