// Import Firebase
import { app, auth, signInWithEmailAndPassword, createUserWithEmailAndPassword, googleProvider, signInWithPopup } from './firebase-config.js';
import { getFirestore, doc, setDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

// Initialize Firestore
const db = getFirestore(app);

// Registration state
let registrationData = {};
let verificationId = null;

// Email validation helper
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Multi-step navigation
window.goToStep = function(stepNumber) {
    document.querySelectorAll('.form-step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById('step' + stepNumber).classList.add('active');
}

// Send OTP
window.sendOTP = async function() {
    const firstName = document.getElementById('firstName').value;
    const lastName = document.getElementById('lastName').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const applicationType = document.getElementById('applicationType').value;
    
    // Validation
    if (!applicationType || !firstName || !lastName || !email || !phone) {
        alert('Please fill in all required fields');
        return;
    }
    
    if (!validateEmail(email)) {
        alert('Please enter a valid email address');
        return;
    }
    
    // Store data
    registrationData = { firstName, lastName, email, phone, applicationType };
    
    try {
        // Call backend to send OTP
        const response = await fetch('/api/send-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('OTP has been sent to your email address. Please check your inbox.');
            goToStep(2);
        } else {
            alert('Failed to send OTP: ' + result.message);
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        alert('Error sending OTP: ' + error.message);
    }
}

// Resend OTP
window.resendOTP = function() {
    sendOTP();
}

// Verify OTP
window.verifyOTP = async function() {
    const otpCode = document.getElementById('otpCode').value;
    
    if (!otpCode || otpCode.length !== 6) {
        alert('Please enter a valid 6-digit OTP code');
        return;
    }
    
    try {
        // Call backend to verify OTP
        const response = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email: registrationData.email,
                otp: otpCode 
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Email verified successfully!');
            goToStep(3);
        } else {
            alert('Verification failed: ' + result.message);
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        alert('Error verifying OTP: ' + error.message);
    }
}

// Signup Form Handler
const signupForm = document.getElementById('signupForm');
if (signupForm) {
    signupForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const address = document.getElementById('address').value;
        const municipality = document.getElementById('municipality').value;
        const province = document.getElementById('province').value;
        const farmSize = document.getElementById('farmSize').value;
        const cropType = document.getElementById('cropType').value;
        const terms = document.querySelector('input[name="terms"]').checked;
        
        // Validation
        if (!address || !municipality || !province || !password || !confirmPassword) {
            alert('Please fill in all required fields');
            return;
        }
        
        if (password.length < 8) {
            alert('Password must be at least 8 characters long');
            return;
        }
        
        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }
        
        if (!terms) {
            alert('Please agree to the Terms of Service and Privacy Policy');
            return;
        }
        
        try {
            // Create user with Firebase Authentication
            const userCredential = await createUserWithEmailAndPassword(auth, registrationData.email, password);
            const user = userCredential.user;
            
            // Save user profile to Firestore
            await setDoc(doc(db, 'users', user.uid), {
                firstName: registrationData.firstName,
                lastName: registrationData.lastName,
                email: registrationData.email,
                phone: registrationData.phone,
                applicationType: registrationData.applicationType,
                address: address,
                municipality: municipality,
                province: province,
                farmSize: farmSize || null,
                cropType: cropType || null,
                userType: 'farmer',
                status: 'pending',
                createdAt: new Date().toISOString()
            });
            
            console.log('Registration successful:', user);
            
            // Redirect to farmer dashboard immediately
            window.location.href = '/farmer/dashboard';
        } catch (error) {
            console.error('Registration error:', error);
            alert('Registration failed: ' + error.message);
        }
    });
}

// Login Form Handler
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        // Frontend validation
        if (!email || !password) {
            alert('Please fill in all fields');
            return;
        }
        
        if (!validateEmail(email)) {
            alert('Please enter a valid email address');
            return;
        }
        
        try {
            // Sign in with Firebase
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;
            
            console.log('Login successful:', user);
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
        } catch (error) {
            console.error('Login error:', error);
            alert('Login failed: ' + error.message);
        }
    });
}

// Google Sign In
const googleButtons = document.querySelectorAll('.btn-google');
googleButtons.forEach(button => {
    button.addEventListener('click', async function() {
        try {
            const result = await signInWithPopup(auth, googleProvider);
            const user = result.user;
            
            console.log('Google sign in successful:', user);
            
            // Redirect to dashboard
            window.location.href = '/dashboard';
            // window.location.href = '/dashboard';
        } catch (error) {
            console.error('Google sign in error:', error);
            alert('Google sign in failed: ' + error.message);
        }
    });
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth page loaded');
});
