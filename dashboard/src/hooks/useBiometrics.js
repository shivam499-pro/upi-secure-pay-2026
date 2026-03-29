import { useState, useRef, useCallback } from 'react';

export function useBiometrics() {
  const [behavioralData, setBehavioralData] = useState({
    typingSpeed: 0,
    formTime: 0,
    mousePauses: 0,
    pasteDetected: false,
    behavioralScore: 100,
    behavioralStatus: 'normal'
  });

  const behavioralRef = useRef({
    formStartTime: null,
    firstFocusTime: null,
    typingStartTime: null,
    typingEndTime: null,
    charCount: 0,
    lastMouseMove: null,
    mouseStopCount: 0,
    isAmountPasted: false,
    isUpiPasted: false,
    fieldFocusOrder: [],
    clickCount: 0
  });

  const calculateScore = useCallback(() => {
    const data = behavioralRef.current;
    const now = Date.now();
    
    // Calculate typing speed
    let typingSpeed = 0;
    if (data.typingStartTime && data.typingEndTime && data.charCount > 0) {
      const timeInSeconds = (data.typingEndTime - data.typingStartTime) / 1000;
      typingSpeed = timeInSeconds > 0 ? data.charCount / timeInSeconds : 0;
    }
    
    // Calculate form completion time
    let formTime = 0;
    if (data.formStartTime) {
      formTime = (now - data.formStartTime) / 1000;
    }
    
    // Calculate score
    let score = 1.0;
    
    if (typingSpeed > 0 && typingSpeed < 1) score -= 0.2;
    if (typingSpeed > 15) score -= 0.1;
    if (data.mouseStopCount > 5) score -= 0.15;
    if (formTime > 0 && formTime < 5) score -= 0.3;
    if (formTime > 300) score -= 0.25;
    if (data.isUpiPasted) score -= 0.2;
    if (data.isAmountPasted) score -= 0.1;
    
    score = Math.max(0.1, Math.min(1.0, score));
    
    // Determine status
    let status = 'normal';
    if (score < 0.4) status = 'suspicious';
    else if (score < 0.7) status = 'warning';
    
    // Update state
    setBehavioralData({
      typingSpeed: typingSpeed.toFixed(1),
      formTime: Math.round(formTime),
      mousePauses: data.mouseStopCount,
      pasteDetected: data.isAmountPasted || data.isUpiPasted,
      behavioralScore: Math.round(score * 100),
      behavioralStatus: status
    });
    
    return score;
  }, []);

  const handleFormFocus = (e) => {
    if (!behavioralRef.current.formStartTime) {
      behavioralRef.current.formStartTime = Date.now();
    }
    if (!behavioralRef.current.firstFocusTime) {
      behavioralRef.current.firstFocusTime = Date.now();
    }
    behavioralRef.current.fieldFocusOrder.push(e?.target?.name || 'unknown');
  };

  const handleTyping = () => {
    if (!behavioralRef.current.typingStartTime) {
      behavioralRef.current.typingStartTime = Date.now();
    }
    behavioralRef.current.charCount++;
    behavioralRef.current.typingEndTime = Date.now();
  };

  const handlePaste = (field) => {
    if (field === 'amount') {
      behavioralRef.current.isAmountPasted = true;
    } else if (field === 'upi' || field === 'receiver_upi') {
      behavioralRef.current.isUpiPasted = true;
    }
  };

  const handleMouseMove = () => {
    const now = Date.now();
    if (behavioralRef.current.lastMouseMove) {
      const timeDiff = now - behavioralRef.current.lastMouseMove;
      if (timeDiff > 2000) { // Pause longer than 2s
        behavioralRef.current.mouseStopCount++;
      }
    }
    behavioralRef.current.lastMouseMove = now;
  };

  const resetBiometrics = () => {
    behavioralRef.current = {
      formStartTime: null,
      firstFocusTime: null,
      typingStartTime: null,
      typingEndTime: null,
      charCount: 0,
      lastMouseMove: null,
      mouseStopCount: 0,
      isAmountPasted: false,
      isUpiPasted: false,
      fieldFocusOrder: [],
      clickCount: 0
    };
    setBehavioralData({
      typingSpeed: 0,
      formTime: 0,
      mousePauses: 0,
      pasteDetected: false,
      behavioralScore: 100,
      behavioralStatus: 'normal'
    });
  };

  return { 
    behavioralData, 
    handleFormFocus, 
    handleTyping, 
    handlePaste, 
    handleMouseMove, 
    calculateScore,
    resetBiometrics 
  };
}
