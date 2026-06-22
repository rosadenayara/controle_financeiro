from flask import Blueprint, request, redirect, url_for, render_template
from flask_login import login_required, current_user
from app.models import Expense
from app.extensions import db

finance_bp = Blueprint("finance", __name__, url_prefix="/finance")

@finance_bp.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        valor = float(request.form["valor"])
        categoria = request.form["categoria"]
        descricao = request.form.get("descricao", "")

        expense = Expense(
            user_id=current_user.id,
            valor=valor,
            categoria=categoria,
            descricao=descricao
        )
        db.session.add(expense)
        db.session.commit()

        from flask import flash
        flash('Despesa adicionada com sucesso.', 'success')
        return redirect(url_for("finance.expenses"))

    return render_template("finance/add_expense.html")

@finance_bp.route("/expenses")
@login_required
def expenses():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    return render_template("finance/expenses.html", expenses=expenses)


@finance_bp.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        # Delete action
        if request.form.get('delete'):
            db.session.delete(expense)
            db.session.commit()
            from flask import flash
            flash('Despesa excluída com sucesso.', 'success')
            return redirect(url_for('finance.expenses'))

        # Update fields
        try:
            valor = float(request.form.get('valor', expense.valor))
        except ValueError:
            valor = expense.valor

        categoria = request.form.get('categoria', expense.categoria)
        descricao = request.form.get('descricao', expense.descricao)

        expense.valor = valor
        expense.categoria = categoria
        expense.descricao = descricao
        db.session.commit()
        from flask import flash
        flash('Despesa atualizada com sucesso.', 'success')

        return redirect(url_for('finance.expenses'))

    return render_template('finance/edit_expense.html', expense=expense)