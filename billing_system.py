import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector

# Database Connection
conn = mysql.connector.connect(host="localhost", user="root", password="Anigopal2901@ani", database="billing_system")
cursor = conn.cursor()

cart = {}


# Load menu items from database
def load_menu():
    cursor.execute("SELECT * FROM menu")
    return cursor.fetchall()


# Update bill list
def update_bill_list():
    bill_list.delete(*bill_list.get_children())
    total_price = 0
    for item_id, data in cart.items():
        bill_list.insert("", "end", values=(data["name"], data["quantity"], f"₹{data['subtotal']}"))
        total_price += data["subtotal"]
    total_label.config(text=f"Total: ₹{total_price}")


# Add item to bill
def add_to_bill(item_id, name, price):
    if item_id in cart:
        cart[item_id]["quantity"] += 1
        cart[item_id]["subtotal"] += price
    else:
        cart[item_id] = {"name": name, "quantity": 1, "subtotal": price}
    update_bill_list()


# Delete item from bill
def delete_from_bill():
    selected_item = bill_list.selection()
    if not selected_item:
        messagebox.showerror("Error", "No item selected")
        return
    item_name = bill_list.item(selected_item)["values"][0]
    for item_id, data in list(cart.items()):
        if data["name"] == item_name:
            del cart[item_id]
            break
    update_bill_list()


# Generate final bill
def generate_bill():
    if not cart:
        messagebox.showerror("Error", "No items in the bill!")
        return
    customer_name = name_entry.get()
    if not customer_name:
        messagebox.showerror("Error", "Enter customer name")
        return
    total_amount = sum(item['subtotal'] for item in cart.values())
    cursor.execute("INSERT INTO orders (customer_name, total_amount) VALUES (%s, %s)", (customer_name, total_amount))
    conn.commit()
    order_id = cursor.lastrowid
    for item_id, data in cart.items():
        cursor.execute("INSERT INTO order_details (order_id, item_id, quantity, subtotal) VALUES (%s, %s, %s, %s)",
                       (order_id, item_id, data['quantity'], data['subtotal']))
    conn.commit()
    messagebox.showinfo("Success", f"Bill generated successfully!\nTotal Amount: ₹{total_amount}")
    cart.clear()
    update_bill_list()
    load_billing_history()


# Load billing history
def load_billing_history():
    history_list.delete(*history_list.get_children())
    cursor.execute("SELECT order_id, customer_name, total_amount FROM orders ORDER BY order_id DESC")
    for row in cursor.fetchall():
        history_list.insert("", "end", values=row)


# View Detailed Bill
def view_bill():
    selected = history_list.selection()
    if not selected:
        messagebox.showerror("Error", "No order selected")
        return
    order_id = history_list.item(selected, "values")[0]
    cursor.execute("SELECT customer_name, total_amount FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()
    bill_textbox.delete("1.0", tk.END)
    bill_textbox.insert(tk.END, f"Customer: {order[0]}\nTotal Amount: ₹{order[1]}\n\nItems:\n")

    cursor.execute("SELECT item_id, quantity, subtotal FROM order_details WHERE order_id = %s", (order_id,))
    items = cursor.fetchall()
    for item in items:
        cursor.execute("SELECT item_name FROM menu WHERE item_id = %s", (item[0],))
        item_name = cursor.fetchone()[0]
        bill_textbox.insert(tk.END, f"{item_name} - Qty: {item[1]}, Subtotal: ₹{item[2]}\n")


# Delete Bill from Database
def delete_bill():
    selected = history_list.selection()
    if not selected:
        messagebox.showerror("Error", "No bill selected")
        return

    try:
        order_id = int(history_list.item(selected, "values")[0])  # Get selected order ID
    except (IndexError, ValueError):
        messagebox.showerror("Error", "Invalid order selection")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Bill ID {order_id}?")
    if not confirm:
        return

    try:
        # Delete order details first due to foreign key constraints
        cursor.execute("DELETE FROM order_details WHERE order_id = %s", (order_id,))
        conn.commit()

        # Delete the order itself
        cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        conn.commit()

        messagebox.showinfo("Success", f"Bill ID {order_id} deleted successfully!")

        # Reorder IDs to maintain sequence
        cursor.execute("SET @count = 0")
        cursor.execute("UPDATE orders SET order_id = @count := @count + 1")
        cursor.execute("ALTER TABLE orders AUTO_INCREMENT = 1")  # Reset AUTO_INCREMENT to max ID + 1
        conn.commit()

        # ✅ Refresh UI
        history_list.delete(selected)
        bill_textbox.delete("1.0", tk.END)
        load_billing_history()  # Reload updated orders

    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", f"Error deleting bill: {err}")



# Billing Page
def billing_page():
    global bill_list, total_label, name_entry, history_list, bill_textbox
    root = tk.Tk()
    root.title("Billing System")
    root.geometry("900x600")
    root.configure(bg="#FFA500")  # Set background color

    button_style = {"bg": "#8B0000", "fg": "white", "activebackground": "#B22222", "activeforeground": "white"}

    # Left Frame (Customer & Menu)
    left_frame = tk.Frame(root, padx=10, pady=10, bg="#FFA500")
    left_frame.pack(side=tk.LEFT, fill=tk.Y)

    tk.Label(left_frame, text="Customer Name:", bg="#8B0000",fg="white").pack()
    name_entry = tk.Entry(left_frame)
    name_entry.pack()

    tk.Label(left_frame, text="Menu Items:", bg="#8B0000",fg="white", font=("Arial", 12, "bold")).pack(pady=5)
    menu_items = load_menu()
    for item_id, name, price, _ in menu_items:
        item_frame = tk.Frame(left_frame, bg="white")
        item_frame.pack(fill=tk.X)
        tk.Label(item_frame, text=f"{name} - ₹{price}", bg="white").pack(side=tk.LEFT)
        tk.Button(item_frame, text="Add", command=lambda id=item_id, n=name, p=price: add_to_bill(id, n, p), **button_style).pack(side=tk.RIGHT)

    # Middle Frame (Bill)
    middle_frame = tk.Frame(root, padx=10, pady=10, bg="#FFA500")
    middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    bill_list = ttk.Treeview(middle_frame, columns=("Item", "Qty", "Subtotal"), show="headings")
    bill_list.heading("Item", text="Item")
    bill_list.heading("Qty", text="Qty")
    bill_list.heading("Subtotal", text="Subtotal")
    bill_list.pack(pady=10)

    total_label = tk.Label(middle_frame, text="Total: ₹0", font=("Arial", 12, "bold"), bg="#8B0000",fg="white")
    total_label.pack()

    tk.Button(middle_frame, text="Delete Item", command=delete_from_bill, **button_style).pack(pady=5)
    tk.Button(middle_frame, text="Generate Bill", command=generate_bill, **button_style).pack(pady=5)

    # Right Frame (Billing History & View Bill Box)
    right_frame = tk.Frame(root, padx=10, pady=10, bg="#FFA500")
    right_frame.pack(side=tk.RIGHT, fill=tk.Y)

    tk.Label(right_frame, text="Billing History:", bg="#8B0000",fg="white", font=("Arial", 12, "bold")).pack()
    history_list = ttk.Treeview(right_frame, columns=("ID", "Customer", "Total"), show="headings")
    history_list.heading("ID", text="ID")
    history_list.heading("Customer", text="Customer")
    history_list.heading("Total", text="Total")
    history_list.pack(pady=10)

    tk.Button(right_frame, text="View Bill", command=view_bill, **button_style).pack(pady=5)
    tk.Button(right_frame, text="Delete Bill", command=delete_bill, **button_style).pack(pady=5)

    bill_textbox = tk.Text(right_frame, height=10, width=40, wrap=tk.WORD)
    bill_textbox.pack()

    load_billing_history()
    root.mainloop()




billing_page()