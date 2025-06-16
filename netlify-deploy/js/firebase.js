// Firebase configuration and authentication
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { 
  getAuth, 
  signInWithRedirect, 
  getRedirectResult,
  GoogleAuthProvider, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

// Firebase configuration - these will be loaded from environment variables
const firebaseConfig = {
  apiKey: "AIzaSyC8MDJp71-_9kPqYtAhni8UmGQDnUzIlYA",
  authDomain: "signo-fleet.firebaseapp.com",
  projectId: "signo-fleet",
  storageBucket: "signo-fleet.firebasestorage.app",
  messagingSenderId: "958560675158",
  appId: "1:958560675158:web:2704882b13d282c57362f7",
  measurementId: "G-RQ5YWWZL4M"

};
// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Google Auth Provider
const googleProvider = new GoogleAuthProvider();

// Authentication state management
let currentUser = null;

// Authentication functions
export const signInWithGoogle = () => {
  return signInWithRedirect(auth, googleProvider);
};

export const signInWithEmail = (email, password) => {
  return signInWithEmailAndPassword(auth, email, password);
};

export const registerWithEmail = (email, password) => {
  return createUserWithEmailAndPassword(auth, email, password);
};

export const logout = () => {
  return signOut(auth);
};

// Handle redirect result after Google sign-in
export const handleRedirectResult = () => {
  return getRedirectResult(auth);
};

// Auth state observer
export const observeAuthState = (callback) => {
  return onAuthStateChanged(auth, (user) => {
    currentUser = user;
    callback(user);
  });
};

// Get current user
export const getCurrentUser = () => {
  return currentUser;
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return currentUser !== null;
};

// Initialize authentication on page load
document.addEventListener('DOMContentLoaded', async () => {
  // Handle redirect result
  try {
    const result = await handleRedirectResult();
    if (result?.user) {
      console.log('User signed in via redirect:', result.user.email);
      await syncUserWithBackend(result.user);
    }
  } catch (error) {
    console.error('Error handling redirect result:', error);
  }

  // Set up auth state observer
  observeAuthState(async (user) => {
    if (user) {
      console.log('User is signed in:', user.email);
      await syncUserWithBackend(user);
      showAuthenticatedContent();
    } else {
      console.log('User is signed out');
      showUnauthenticatedContent();
    }
  });
});

// Sync Firebase user with Django backend
async function syncUserWithBackend(user, additionalData = {}) {
  try {
    const idToken = await user.getIdToken();
    
    const requestData = {
      uid: user.uid,
      email: user.email,
      display_name: user.displayName,
      photo_url: user.photoURL,
      id_token: idToken,
      ...additionalData
    };
    
    const response = await fetch('/fleet/api/auth/firebase-login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
      },
      body: JSON.stringify(requestData)
    });
    
    if (response.ok) {
      const userData = await response.json();
      console.log('User synced with backend:', userData);
      return userData;
    } else {
      console.error('Failed to sync user with backend');
    }
  } catch (error) {
    console.error('Error syncing user with backend:', error);
  }
}

// Show content for authenticated users
function showAuthenticatedContent() {
  const loginSection = document.getElementById('login-section');
  const dashboardSection = document.getElementById('dashboard-section');
  const userInfo = document.getElementById('user-info');
  
  if (loginSection) loginSection.style.display = 'none';
  if (dashboardSection) dashboardSection.style.display = 'block';
  
  if (userInfo && currentUser) {
    userInfo.innerHTML = `
      <div class="d-flex align-items-center">
        <img src="${currentUser.photoURL || '/static/img/default-avatar.png'}" 
             class="rounded-circle me-2" width="32" height="32" alt="Profile">
        <span class="fw-medium">${currentUser.displayName || currentUser.email}</span>
        <button class="btn btn-sm btn-outline-secondary ms-2" onclick="handleLogout()">
          <i class="fas fa-sign-out-alt"></i> Logout
        </button>
      </div>
    `;
  }
}

// Show content for unauthenticated users
function showUnauthenticatedContent() {
  const loginSection = document.getElementById('login-section');
  const dashboardSection = document.getElementById('dashboard-section');
  
  if (loginSection) loginSection.style.display = 'block';
  if (dashboardSection) dashboardSection.style.display = 'none';
}

// Global functions for UI interaction
window.handleGoogleLogin = async () => {
  try {
    await signInWithGoogle();
  } catch (error) {
    console.error('Google login error:', error);
    alert('Failed to sign in with Google. Please try again.');
  }
};

// window.handleEmailLogin = async (event) => {
//   event.preventDefault();
//   const email = document.getElementById('email').value;
//   const password = document.getElementById('password').value;
  
//   try {
//     await signInWithEmail(email, password);
//   } catch (error) {
//     console.error('Email login error:', error);
//     alert('Failed to sign in. Please check your credentials.');
//   }
// };

window.handleEmailRegister = async (event) => {
  event.preventDefault();
  const email = document.getElementById('register-email').value;
  const password = document.getElementById('register-password').value;
  
  try {
    await registerWithEmail(email, password);
  } catch (error) {
    console.error('Registration error:', error);
    alert('Failed to register. Please try again.');
  }
};

// Register with email, password and role-specific data
window.registerWithEmailAndRole = async (email, password, userData) => {
  const userCredential = await createUserWithEmailAndPassword(auth, email, password);
  const user = userCredential.user;
  
  // Sync with backend including role data
  await syncUserWithBackend(user, userData);
  return user;
};

window.handleLogout = async () => {
  try {
    await logout();
    window.location.reload();
  } catch (error) {
    console.error('Logout error:', error);
  }
};