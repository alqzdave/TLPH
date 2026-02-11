import { auth, db, storage, onAuthStateChanged } from './firebase-config.js';
import { collection, addDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { ref, uploadBytes, getDownloadURL } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-storage.js";

/**
 * Get current user data
 */
export function getCurrentUser() {
    return new Promise((resolve) => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            unsubscribe();
            resolve(user);
        });
    });
}

/**
 * Upload a single file to Firebase Storage
 */
async function uploadFileToStorage(file, userId, collectionType, filename) {
    try {
        const timestamp = Date.now();
        const fileExtension = file.name.split('.').pop();
        const uniqueFilename = `${filename || file.name.split('.')[0]}_${timestamp}.${fileExtension}`;
        const storagePath = `license-applications/${userId}/${collectionType}/${uniqueFilename}`;
        
        const storageRef = ref(storage, storagePath);
        await uploadBytes(storageRef, file);
        const downloadUrl = await getDownloadURL(storageRef);
        
        return {
            name: file.name,
            size: file.size,
            type: file.type,
            downloadUrl: downloadUrl,
            storagePath: storagePath,
            uploadedAt: new Date().toISOString()
        };
    } catch (error) {
        console.error('Error uploading file:', error);
        throw new Error(`Failed to upload file: ${file.name}`);
    }
}

/**
 * Upload multiple files to Firebase Storage
 */
async function uploadMultipleFiles(fileList, userId, collectionType, filenamePrefix) {
    try {
        const uploadedFiles = [];
        
        for (let file of fileList) {
            const fileData = await uploadFileToStorage(file, userId, collectionType, filenamePrefix);
            uploadedFiles.push(fileData);
        }
        
        return uploadedFiles;
    } catch (error) {
        console.error('Error uploading multiple files:', error);
        throw error;
    }
}

/**
 * Save license application data to Firestore
 */
export async function saveLicenseApplicationToFirebase(formData) {
    try {
        // Get current user
        const user = await getCurrentUser();
        
        if (!user) {
            throw new Error('User not authenticated');
        }
        
        const userId = user.uid;
        const userEmail = user.email;
        const applicationType = formData.applicationType || 'license';
        
        // Process file uploads first
        let uploadedFiles = {};
        
        // Upload main/proof documents
        if (formData.mainProofFiles && formData.mainProofFiles.length > 0) {
            uploadedFiles.mainProof = await uploadMultipleFiles(
                formData.mainProofFiles,
                userId,
                applicationType,
                'proof'
            );
        }
        
        // Upload previous permit if exists
        if (formData.prevPermitFile) {
            uploadedFiles.prevPermit = await uploadFileToStorage(
                formData.prevPermitFile,
                userId,
                applicationType,
                'previous-permit'
            );
        }
        
        // Prepare application data for Firestore
        const applicationData = {
            userId: userId,
            userEmail: userEmail,
            applicationType: applicationType,
            formData: {
                ...formData,
                // Replace file objects with null, we only store file metadata
                mainProofFiles: null,
                prevPermitFile: null
            },
            uploadedFiles: uploadedFiles,
            status: 'pending',
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp(),
            paymentStatus: 'pending',
            externalId: formData.externalId || null,
            amount: formData.amount || null
        };
        
        // Save to Firestore
        const licenseCollection = collection(db, 'license_applications');
        const docRef = await addDoc(licenseCollection, applicationData);
        
        console.log('License application saved to Firebase:', docRef.id);
        
        return {
            success: true,
            documentId: docRef.id,
            message: 'Application data saved successfully'
        };
    } catch (error) {
        console.error('Error saving license application:', error);
        throw error;
    }
}

/**
 * Collect form data from license application form
 */
export function collectEnvironmentClearanceFormData() {
    try {
        const complianceType = document.getElementById('complianceType');
        const appType = document.getElementById('appType');
        const mainProof = document.getElementById('mainProof');
        const prevPermitInput = document.getElementById('prevPermitInput');
        const xenditAmount = document.getElementById('xendit_raw_amount');
        
        if (!complianceType || !appType || !mainProof) {
            throw new Error('Required form fields not found');
        }
        
        const formData = {
            applicationType: 'environmental-clearance',
            complianceType: complianceType.value,
            applicationType: appType.value,
            mainProofFiles: mainProof.files,
            prevPermitFile: prevPermitInput && prevPermitInput.files.length > 0 ? prevPermitInput.files[0] : null,
            amount: xenditAmount ? parseInt(xenditAmount.value) : null,
            submittedAt: new Date().toISOString()
        };
        
        return formData;
    } catch (error) {
        console.error('Error collecting form data:', error);
        throw error;
    }
}

/**
 * Collect form data from a generic license form
 */
export function collectLicenseFormData(formSelector = 'form', fieldsToExtract = []) {
    try {
        const form = document.querySelector(formSelector);
        if (!form) {
            throw new Error(`Form not found with selector: ${formSelector}`);
        }
        
        const formData = new FormData(form);
        const data = {
            applicationType: 'license',
            submittedAt: new Date().toISOString(),
            formFields: {}
        };
        
        // Collect text/select inputs
        form.querySelectorAll('input[type="text"], input[type="email"], input[type="number"], select, textarea').forEach(field => {
            if (field.name) {
                data.formFields[field.name] = field.value;
            }
        });
        
        // Collect file inputs and get files
        const fileInputs = {};
        form.querySelectorAll('input[type="file"]').forEach(field => {
            if (field.files && field.files.length > 0) {
                fileInputs[field.id] = field.files;
            }
        });
        
        // Add specific file references for easier access
        if (fileInputs.mainProof) {
            data.mainProofFiles = fileInputs.mainProof;
        }
        if (fileInputs.prevPermitInput) {
            data.prevPermitFile = fileInputs.prevPermitInput[0];
        }
        data.files = fileInputs;
        
        // Get xendit amount if available
        const xenditAmount = document.getElementById('xendit_raw_amount');
        if (xenditAmount) {
            data.amount = parseInt(xenditAmount.value);
        }
        
        // Detect application type from page heading
        const pageHeading = Array.from(document.querySelectorAll("h1, h2")).find(
            (heading) => !heading.closest("header")
        );
        
        if (pageHeading) {
            const heading = pageHeading.textContent.toLowerCase();
            if (heading.includes('environmental') || heading.includes('clearance')) {
                data.applicationType = 'environmental-clearance';
            } else if (heading.includes('fisheries')) {
                data.applicationType = 'fisheries-license';
            } else if (heading.includes('forest') || heading.includes('timber')) {
                data.applicationType = 'forest-license';
            } else if (heading.includes('livestock') || heading.includes('farm')) {
                data.applicationType = 'livestock-license';
            } else if (heading.includes('wildlife')) {
                data.applicationType = 'wildlife-license';
            }
        }
        
        return data;
    } catch (error) {
        console.error('Error collecting form data:', error);
        throw error;
    }
}
