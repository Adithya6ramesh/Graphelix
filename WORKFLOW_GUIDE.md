# 🔄 Workflow Transition Quick Reference

## Current Error Resolution

### ❌ Error: "Transition from submitted to rejected is not allowed"
**Problem:** You're trying to reject a case directly from SUBMITTED state.
**Solution:** First transition to IN_REVIEW, then reject.

**Correct sequence:**
1. SUBMITTED → IN_REVIEW (Officer starts review)
2. IN_REVIEW → REJECTED (Officer rejects after review)

### ❌ Error: "Transition from in_review to in_review is not allowed"
**Problem:** Case is already in IN_REVIEW state.
**Solution:** Choose a different target state from the available options.

**From IN_REVIEW, you can go to:**
- APPROVED (Officer approves)
- REJECTED (Officer rejects)
- MATCH_FOUND (Officer finds matching content)
- ESCALATED (Officer escalates to admin)

## 📋 Complete Workflow Guide

### 🟢 Valid Transitions

```
SUBMITTED
├─→ IN_REVIEW (Officer/Admin)
└─→ ESCALATED (Admin only)

IN_REVIEW
├─→ APPROVED (Officer/Admin)
├─→ REJECTED (Officer/Admin)
├─→ MATCH_FOUND (Officer/Admin)
└─→ ESCALATED (Officer/Admin)

ESCALATED
├─→ APPROVED (Admin only)
├─→ REJECTED (Admin only)
└─→ IN_REVIEW (Admin only)

MATCH_FOUND
├─→ COMPLETED (Officer/Admin)
└─→ ESCALATED (Officer/Admin)

APPROVED
└─→ COMPLETED (Officer/Admin)

REJECTED
└─→ COMPLETED (Officer/Admin)
```

### 🎯 Common Workflows

**Normal Approval Flow:**
SUBMITTED → IN_REVIEW → APPROVED → COMPLETED

**Normal Rejection Flow:**
SUBMITTED → IN_REVIEW → REJECTED → COMPLETED

**Content Found Flow:**
SUBMITTED → IN_REVIEW → MATCH_FOUND → COMPLETED

**Escalation Flow:**
SUBMITTED → IN_REVIEW → ESCALATED → APPROVED → COMPLETED

**Immediate Admin Escalation:**
SUBMITTED → ESCALATED → APPROVED → COMPLETED

## 🔧 How to Fix Your Current Issues

1. **Check case current state** first
2. **Use only valid transitions** from that state
3. **Follow the workflow sequence** - don't skip steps
4. **Use the transitions API** to see available options

### Example: To reject a SUBMITTED case
```
Step 1: PUT /api/cases/{id}/status {"state": "in_review"}
Step 2: PUT /api/cases/{id}/status {"state": "rejected"}
```

### Example: If case is already IN_REVIEW
```
Available options:
- {"state": "approved"}
- {"state": "rejected"} 
- {"state": "match_found"}
- {"state": "escalated"}
```

The workflow system is working correctly - it's enforcing proper business logic!
