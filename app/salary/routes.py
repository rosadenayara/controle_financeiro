from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Salary, Goal
from app.extensions import db
from app.taxes.calculos import calcular_salario, progresso_meta
from app.taxes.calculos import calcular_inss, calcular_irrf

salary_bp = Blueprint('salary', __name__)

@salary_bp.route("/", methods=["GET", "POST"])
@login_required
def salary():
    resultado = None
    metas = None
    salario_atual = Salary.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        try:
            bruto = _parse_number(request.form.get("bruto", ""))
        except ValueError:
            flash("Valor de salário inválido. Use apenas números, ex: 2500.50 ou 2.500,50.")
            return render_template("salary/index.html", resultado=None, metas=[], salario_atual=salario_atual)

        resultado = calcular_salario(bruto)

        if salario_atual:
            salario_atual.bruto = resultado["bruto"]
            salario_atual.liquido = resultado["liquido"]
        else:
            salario_atual = Salary(
                user_id=current_user.id,
                bruto=resultado["bruto"],
                liquido=resultado["liquido"]
            )
            db.session.add(salario_atual)

        db.session.commit()
        flash('Salário salvo com sucesso.', 'success')

    # Calcular progresso das metas (a propriedade `progresso` do modelo já calcula)
    metas = Goal.query.filter_by(user_id=current_user.id).all()

    return render_template("salary/index.html", resultado=resultado, metas=metas, salario_atual=salario_atual)


@salary_bp.route("/edit-salary", methods=["GET", "POST"])
@login_required
def edit_salary():
    salario_atual = Salary.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == "POST":
        # Delete action
        if request.form.get('delete'):
            db.session.delete(salario_atual)
            db.session.commit()
            flash('Salário removido com sucesso.', 'success')
            return redirect(url_for('salary.salary'))

        try:
            bruto = _parse_number(request.form.get("bruto", ""))
        except ValueError:
            flash("Valor de salário inválido. Use apenas números, ex: 2500.50 ou 2.500,50.")
            return render_template("salary/edit_salary.html", salario=salario_atual)

        resultado = calcular_salario(bruto)

        salario_atual.bruto = resultado["bruto"]
        salario_atual.liquido = resultado["liquido"]
        db.session.commit()

        flash('Salário atualizado com sucesso.', 'success')
        return redirect(url_for("salary.salary"))

    return render_template("salary/edit_salary.html", salario=salario_atual)

@salary_bp.route("/add-goal", methods=["GET", "POST"])
@login_required
def add_goal():
    if request.method == "POST":
        nome = request.form["nome"]
        try:
            valor_objetivo = _parse_number(request.form.get("valor_objetivo", ""))
        except ValueError:
            flash("Valor objetivo inválido. Use apenas números, ex: 10000.00 ou 10.000,00.")
            return redirect(url_for("salary.add_goal"))

        try:
            valor_atual = _parse_number(request.form.get("valor_atual", "0"), default=0)
        except ValueError:
            flash("Valor atual inválido. Use apenas números, ex: 0.00 ou 0,00.")
            return redirect(url_for("salary.add_goal"))

        goal = Goal(
            user_id=current_user.id,
            nome=nome,
            valor_objetivo=valor_objetivo,
            valor_atual=valor_atual
        )
        db.session.add(goal)
        db.session.commit()

        flash('Meta criada com sucesso.', 'success')
        return redirect(url_for("salary.goals"))

    return render_template("salary/add_goal.html")

@salary_bp.route("/edit-goal/<int:goal_id>", methods=["GET", "POST"])
@login_required
def edit_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        # Delete action
        if request.form.get('delete'):
            db.session.delete(goal)
            db.session.commit()
            flash('Meta excluída com sucesso.', 'success')
            return redirect(url_for('salary.goals'))

        try:
            valor_atual = _parse_number(request.form.get("valor_atual", ""))
        except ValueError:
            flash("Valor atual inválido. Use apenas números, ex: 0.00 ou 0,00.")
            return render_template("salary/edit_goal.html", goal=goal, progresso=0, restante=goal.valor_objetivo - goal.valor_atual)

        goal.valor_atual = valor_atual
        db.session.commit()

        flash('Meta atualizada com sucesso.', 'success')
        return redirect(url_for("salary.goals"))

    progresso = (goal.valor_atual / goal.valor_objetivo) * 100 if goal.valor_objetivo > 0 else 0
    restante = goal.valor_objetivo - goal.valor_atual

    return render_template("salary/edit_goal.html", goal=goal, progresso=round(progresso, 1), restante=round(restante, 2))


def _parse_number(value: str, default=None) -> float:
    """Parse string numbers tolerant to thousand separators and comma decimals.

    Examples accepted: '1234.56', '1.234,56', '1234,56', '1000'
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if default is not None:
            return default
        raise ValueError("empty")

    s = str(value).strip()
    # remove currency symbols and spaces
    s = s.replace('R$', '').replace(' ', '')

    # If both separators present, assume '.' is thousands and ',' is decimal
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # If only comma present, treat it as decimal separator
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        # if only dot present, keep as is

    try:
        return float(s)
    except ValueError:
        raise

@salary_bp.route("/goals")
@login_required
def goals():
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    goals_com_progresso = []
    
    for goal in goals:
        # A propriedade `progresso` em `Goal` já retorna o valor arredondado
        goals_com_progresso.append(goal)
        
    return render_template("salary/goals.html", goals=goals_com_progresso)


@salary_bp.route('/painel-impostos')
@login_required
def painel_impostos():
    salario_usuario = Salary.query.filter_by(user_id=current_user.id).first()
    
    if not salario_usuario:
        return render_template('salary/painel_impostos.html', cadastrado=False)
    
    bruto = salario_usuario.bruto 
    
    # Chamando as suas funções do arquivo services.py
    inss = calcular_inss(bruto)
    irrf = calcular_irrf(bruto) 
    liquido = bruto - inss - irrf
    
    total_impostos = inss + irrf
    aliquota_efetiva = (total_impostos / bruto) * 100 if bruto > 0 else 0
    
    return render_template(
        'salary/painel_impostos.html',
        cadastrado=True,
        bruto=bruto,
        inss=inss,
        irrf=irrf,
        liquido=liquido,
        total_impostos=total_impostos,
        aliquota_efetiva=round(aliquota_efetiva, 2)
    )

