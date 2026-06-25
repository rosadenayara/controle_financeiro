from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Salary, Goal
from app.extensions import db
from app.taxes.calculos import (
    progresso_meta, resumo_clt, resumo_pj_simples, resumo_mei
)

salary_bp = Blueprint('salary', __name__)


@salary_bp.route("/", methods=["GET", "POST"])
@login_required
def salary():
    resultado    = None
    salario_atual = Salary.query.filter_by(user_id=current_user.id).first()
    regime_atual  = (
        (salario_atual.regime if salario_atual and salario_atual.regime else None)
        or current_user.perfil_tributario
        or "CLT"
    ).lower()

    if request.method == "POST":
        regime = request.form.get("regime", "clt").lower()

        # Fallback: detecta pelo campo preenchido quando JS não atualizou o hidden input.
        if regime == "clt" and not request.form.get("bruto", "").strip():
            if request.form.get("faturamento_pj", "").strip():
                regime = "pj"
            elif request.form.get("faturamento_mei", "").strip():
                regime = "mei"

        try:
            if regime == "clt":
                bruto        = _parse_number(request.form.get("bruto", ""))
                resultado    = resumo_clt(bruto)
                db_bruto     = resultado["bruto"]
                db_liquido   = resultado["liquido"]
                db_inss      = resultado["inss"]
                db_irrf      = resultado["irpf"]
                db_fgts      = resultado["fgts"]
                db_pro_labore     = None
                db_tipo_atividade = None

            elif regime == "pj":
                fat          = _parse_number(request.form.get("faturamento_pj", ""))
                pl           = _parse_number(request.form.get("pro_labore", "0"), default=0)
                resultado    = resumo_pj_simples(fat, pl)
                db_bruto     = resultado["faturamento"]
                db_liquido   = resultado["liquido_estimado"]
                db_inss      = resultado["inss_pro_labore"]
                db_irrf      = resultado["irpf_pro_labore"]
                db_fgts      = None
                db_pro_labore     = pl
                db_tipo_atividade = None

            elif regime == "mei":
                fat          = _parse_number(request.form.get("faturamento_mei", ""))
                tipo         = request.form.get("tipo_atividade", "comercio")
                resultado    = resumo_mei(fat, tipo)
                db_bruto     = resultado["faturamento"]
                db_liquido   = resultado["liquido_estimado"]
                db_inss      = None
                db_irrf      = None
                db_fgts      = None
                db_pro_labore     = None
                db_tipo_atividade = tipo

            else:
                flash("Regime inválido.", "danger")
                metas = Goal.query.filter_by(user_id=current_user.id).all()
                return render_template("salary/index.html", resultado=None,
                                       metas=metas, salario_atual=salario_atual,
                                       regime_atual=regime_atual)

        except ValueError:
            flash("Valor inválido. Use apenas números, ex: 2500.50 ou 2.500,50.", "danger")
            metas = Goal.query.filter_by(user_id=current_user.id).all()
            return render_template("salary/index.html", resultado=None,
                                   metas=metas, salario_atual=salario_atual,
                                   regime_atual=regime_atual)

        current_user.perfil_tributario = regime.upper()

        if salario_atual:
            salario_atual.regime         = regime.upper()
            salario_atual.bruto          = db_bruto
            salario_atual.liquido        = db_liquido
            salario_atual.inss           = db_inss
            salario_atual.irrf           = db_irrf
            salario_atual.fgts           = db_fgts
            salario_atual.pro_labore     = db_pro_labore
            salario_atual.tipo_atividade = db_tipo_atividade
        else:
            db.session.add(Salary(
                user_id=current_user.id,
                regime=regime.upper(),
                bruto=db_bruto, liquido=db_liquido,
                inss=db_inss, irrf=db_irrf, fgts=db_fgts,
                pro_labore=db_pro_labore,
                tipo_atividade=db_tipo_atividade,
            ))

        db.session.commit()
        flash("Salário salvo com sucesso.", "success")
        # PRG: redireciona para GET — assim o card de resumo aparece imediatamente
        return redirect(url_for("salary.salary"))

    metas = Goal.query.filter_by(user_id=current_user.id).all()
    return render_template("salary/index.html", resultado=None, metas=metas,
                           salario_atual=salario_atual, regime_atual=regime_atual)


@salary_bp.route("/edit-salary")
@login_required
def edit_salary():
    """Redireciona para a página de salário (formulário já permite editar)."""
    return redirect(url_for("salary.salary"))


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
        if request.form.get('delete'):
            db.session.delete(goal)
            db.session.commit()
            flash('Meta excluída com sucesso.', 'success')
            return redirect(url_for('salary.goals'))

        try:
            valor_atual = _parse_number(request.form.get("valor_atual", ""))
        except ValueError:
            flash("Valor atual inválido. Use apenas números, ex: 0.00 ou 0,00.")
            return render_template("salary/edit_goal.html", goal=goal,
                                   progresso=0, restante=goal.valor_objetivo - goal.valor_atual)

        goal.valor_atual = valor_atual
        db.session.commit()

        flash('Meta atualizada com sucesso.', 'success')
        return redirect(url_for("salary.goals"))

    progresso = (goal.valor_atual / goal.valor_objetivo) * 100 if goal.valor_objetivo > 0 else 0
    restante  = goal.valor_objetivo - goal.valor_atual

    return render_template("salary/edit_goal.html", goal=goal,
                           progresso=round(progresso, 1), restante=round(restante, 2))


@salary_bp.route("/goals")
@login_required
def goals():
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    return render_template("salary/goals.html", goals=goals)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_number(value: str, default=None) -> float:
    """Parse strings numéricas tolerante a separadores BR (1.234,56) e EN (1234.56)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if default is not None:
            return default
        raise ValueError("empty")

    s = str(value).strip().replace('R$', '').replace(' ', '')

    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s and '.' not in s:
        s = s.replace(',', '.')

    try:
        return float(s)
    except ValueError:
        raise
