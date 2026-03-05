const API_URL = "/users";
const form = document.getElementById("userForm");
const tableBody = document.querySelector("#usersTable tbody");

// Load all users
async function loadUsers() {
  try {
    const res = await fetch(API_URL);
    const users = await res.json();

    tableBody.innerHTML = "";
    users.forEach((u) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${u.id}</td>
        <td>${u.username}</td>
        <td>${u.department}</td>
        <td>${u.created_by || "-"}</td>
        <td>
          <button onclick="editUser(${u.id}, '${u.username.replace(/'/g, "\\'")}', '${u.department.replace(/'/g, "\\'")}')">Edit</button>
          <button onclick="deleteUser(${u.id})">Delete</button>
        </td>
      `;
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading users:", error);
  }
}


// Add or update user
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const id = document.getElementById("userId").value;
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const department = document.getElementById("department").value;

  const userData = { username, password, department };

  try {
    let res, data;
    if (id) {
      // Update user (PUT)
      if (!password) delete userData.password;
      res = await fetch(`${API_URL}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData),
      });
      data = await res.json();
      alert(data.message || "User updated!");
    } else {
      // Create user (POST)
      res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData),
      });
      data = await res.json();
      alert(data.message || "User added!");
    }

    form.reset();
    document.getElementById("userId").value = "";
    loadUsers();
  } catch (err) {
    alert("Error: " + err.message);
  }
});

// Edit user
function editUser(id, username, department) {
  console.log("Editing user:", id);
  document.getElementById("userId").value = id;
  document.getElementById("username").value = username;
  document.getElementById("department").value = department;
}

// Delete user
async function deleteUser(id) {
  if (confirm("Are you sure you want to delete this user?")) {
    const res = await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    const data = await res.json();
    alert(data.message || "User deleted!");
    loadUsers();
  }
}

body {
  margin: 0;
  font-family: 'Segoe UI', sans-serif;
  background-color: #003366;
  color: #fff;
}

/* HEADER */
.header {
  width: 100%;
  background: #fff;
  color: #003366;
  padding: 10px 0;
  border-bottom: 3px solid #ffcc00;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.header img {
  height: 60px;
  width: auto;
}

.header-text h1 {
  margin: 0;
  font-size: 20px;
  color: #003366;
}

.header-text p {
  margin: 0;
  font-size: 14px;
  color: #333;
}

/* MAIN */
main {
  min-height: calc(100vh - 180px);
  padding: 20px;
}

/* FOOTER */
footer {
  background: #002244;
  color: #ffffff;
  text-align: center;
  font-size: 12px;
  line-height: 1.6;
  padding: 12px;
  width: 100%;
  border-top: 2px solid #ffcc00;
}

footer span {
  color: #ffcc00;
  font-weight: bold;
}


// Load on page start
loadUsers();
