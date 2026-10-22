/**
 * Trackside — Admin Dashboard
 *
 * Pit-Wall System Administration & Hardware Control:
 * - IoT Hardware connectivity pings and self-test diagnostics
 * - Intradomain user account provisioning & role management (Admin only)
 * - Security audit logging & active telemetry node diagnostics
 */

import { Users, Plus, X } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { Panel } from "../../components/ui/panel";
import { TutorialCallout } from "../../components/ui/tutorial-callout";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { useAuth } from "../../lib/auth";
import { useAdminDashboard } from "./hooks/use-admin-dashboard";
import { DeviceDiagnosticPanel } from "./components/device-diagnostic-panel";
import { UserCreateForm } from "./components/user-create-form";
import { UserManagementTable } from "./components/user-management-table";
import { UserDeleteDialog } from "./components/user-delete-dialog";
import { AuditAndDiagnostics } from "./components/audit-and-diagnostics";

export function AdminDashboard() {
  const { user: currentUser } = useAuth();
  const {
    users,
    devices,
    refreshDevices,
    fetchError,
    setFetchError,
    showCreateForm,
    setShowCreateForm,
    name,
    setName,
    email,
    setEmail,
    role,
    setRole,
    password,
    setPassword,
    errorMsg,
    copied,
    successData,
    handleCreateAccount,
    copyCredentials,
    editingUserId,
    setEditingUserId,
    editName,
    setEditName,
    editEmail,
    setEditEmail,
    editCode,
    setEditCode,
    editError,
    startEdit,
    handleSaveEdit,
    confirmModal,
    setConfirmModal,
    handleToggleDeactivate,
    executeToggleDeactivate,
    userToDelete,
    deleteNotice,
    openDelete,
    closeDelete,
    handleDeleted,
    deactivateInstead,
    auditLogs,
    audit30DayCount,
    diagnostics,
  } = useAdminDashboard();

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none">
      {/* Background Slanted Streams */}
      <div className="bg-slant-container">
        <div className="bg-slant-stream-top" />
        <div className="bg-slant-stream-bottom" />
      </div>

      <div className="relative z-10">
        <TopBar />
        <TutorialCallout role="admin" />

        <main className="max-w-6xl mx-auto px-4 py-5 space-y-4 animate-fade-in">
          {/* IoT Hardware Status Pings & Diagnostics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {devices.length === 0 ? (
              <div
                data-testid="admin-devices-empty-state"
                className="col-span-1 sm:col-span-3 text-center py-4 text-xs font-mono text-[#7C8898] border border-dashed border-[#232B35] rounded-lg"
              >
                No IoT devices registered. Waiting for provisioning.
              </div>
            ) : (
              devices.map((device) => (
                <DeviceDiagnosticPanel
                  key={device.id}
                  device={device}
                  activeDrivers={users.filter(
                    (u) => u.role === "driver" && u.is_active !== false && u.status !== "Inactive"
                  )}
                  onDeviceUpdated={refreshDevices}
                />
              ))
            )}
          </div>

          {/* Intradomain User Management Table */}
          <Panel
            testId="admin-user-management-panel"
            title="User Management & Role Provisioning"
            icon={Users}
            right={
              <button
                data-testid="admin-add-account-btn"
                onClick={() => setShowCreateForm(!showCreateForm)}
                className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded cursor-pointer transition-colors"
                style={{
                  color: "#3FA6E0",
                  border: "1px solid #3FA6E044",
                  background: "#3FA6E010",
                }}
              >
                {showCreateForm ? <X size={12} /> : <Plus size={12} />}
                {showCreateForm ? "Cancel" : "Add Account"}
              </button>
            }
          >
            {/* Inline Account Creation Form & Credentials */}
            <UserCreateForm
              showCreateForm={showCreateForm}
              name={name}
              setName={setName}
              email={email}
              setEmail={setEmail}
              role={role}
              setRole={setRole}
              password={password}
              setPassword={setPassword}
              errorMsg={errorMsg}
              handleCreateAccount={handleCreateAccount}
              successData={successData}
              copied={copied}
              copyCredentials={copyCredentials}
            />

            {deleteNotice && (
              <div data-testid="admin-delete-notice" className="mb-4 p-3 rounded text-xs font-mono bg-[#33D17E]/10 border border-[#33D17E]/40 text-[#33D17E]">
                {deleteNotice}
              </div>
            )}

            {/* Users Roster: Mobile Card View (< md) & Desktop Table View (>= md) */}
            <UserManagementTable
              users={users}
              currentUser={currentUser}
              fetchError={fetchError}
              setFetchError={setFetchError}
              editingUserId={editingUserId}
              setEditingUserId={setEditingUserId}
              editName={editName}
              setEditName={setEditName}
              editEmail={editEmail}
              setEditEmail={setEditEmail}
              editCode={editCode}
              setEditCode={setEditCode}
              editError={editError}
              startEdit={startEdit}
              handleSaveEdit={handleSaveEdit}
              handleToggleDeactivate={handleToggleDeactivate}
              onDelete={openDelete}
            />
          </Panel>

          {/* System Analytics & Audit Overview */}
          <AuditAndDiagnostics
            auditLogs={auditLogs}
            audit30DayCount={audit30DayCount}
            diagnostics={diagnostics}
          />
        </main>
      </div>

      {/* Permanent delete dialog */}
      {userToDelete && (
        <UserDeleteDialog
          user={userToDelete}
          onClose={closeDelete}
          onDeleted={handleDeleted}
          onDeactivateInstead={deactivateInstead}
        />
      )}

      {/* Deactivate/Reactivate Confirm Dialog Modal */}
      <ConfirmDialog
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.isCurrentlyActive ? "Deactivate Account" : "Reactivate Account"}
        variant={confirmModal.isCurrentlyActive ? "danger" : "primary"}
        onConfirm={executeToggleDeactivate}
        onCancel={() => setConfirmModal((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}
