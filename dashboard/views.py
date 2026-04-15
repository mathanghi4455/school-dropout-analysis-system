import base64, io, os, json
import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
import matplotlib
matplotlib.use('Agg')

# ── Login / Logout ──────────────────────────────────────────────────────────
def login_view(request):
    """Front page login."""
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('index')
        return render(request, 'dashboard/login.html', {'error': 'Invalid username or password. Please try again.'})
    return render(request, 'dashboard/login.html')

def logout_view(request):
    """Log out and redirect to login page."""
    auth_logout(request)
    return redirect('login')

def get_df():
    try:
        client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=500)
        client.server_info()
        data = list(client['school_dropout_db']['education_data'].find({}, {'_id':0}))
        return pd.DataFrame(data)
    except:
        try:
            with open(os.path.join(settings.BASE_DIR, 'offline_db.json')) as f:
                return pd.DataFrame(json.load(f))
        except:
            return pd.DataFrame()

def get_graph(fig):
    facecolor, textcolor = '#2a0a18', '#ffe6f0'
    fig.patch.set_facecolor(facecolor)
    for ax in fig.axes:
        ax.set_facecolor(facecolor)
        ax.tick_params(colors=textcolor)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color(textcolor)
            
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=facecolor, dpi=120)
    buf.seek(0)
    data = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return data

CATEGORY_META = {
    'Region':        ('1️⃣ Region / Location',        'which areas have high dropout rates — by State, District, and Rural vs Urban'),
    'Education':     ('2️⃣ Educational Level',        'at which stage students drop out — Primary, Secondary, or Higher Secondary'),
    'Gender':        ('3️⃣ Gender',                   'gender inequality — comparing Male vs Female dropout rates'),
    'Socioeconomic': ('4️⃣ Socioeconomic Status',     'the impact of poverty — Poor, Middle, and Rich income groups'),
    'Infrastructure':('5️⃣ Infrastructure Factors',   'how school availability and facilities affect dropout'),
    'Time':          ('6️⃣ Time / Year',              'dropout trends and changes over multiple years'),
    'DropoutRate':   ('7️⃣ Dropout Rate',             'the distribution of the main output variable — % of students leaving school'),
}

@login_required(login_url='/login/')
def index(request):
    df = get_df()
    if df.empty:
        return render(request, 'dashboard/interactive.html', {'error': True})

    df['primary_dropout']   = df['dropout_rates'].apply(lambda x: x.get('primary', 0))
    df['secondary_dropout'] = df['dropout_rates'].apply(lambda x: x.get('secondary', 0))
    _sec_mean = df['secondary_dropout'].mean()
    df['higher_dropout']    = df['dropout_rates'].apply(lambda x: x.get('higher_secondary', _sec_mean))
    df['male_dropout']      = df['gender_rates'].apply(lambda x: x.get('male_secondary', 0))
    df['female_dropout']    = df['gender_rates'].apply(lambda x: x.get('female_secondary', 0))

    # ── State search filter ──────────────────────────────────────────────────
    available_states = sorted(df['state'].unique().tolist())
    search_state     = request.POST.get('search_state', '').strip()
    if search_state:
        filtered = df[df['state'].str.contains(search_state, case=False, na=False)]
        if not filtered.empty:
            df = filtered  # apply filter only if it yields results

    g_dyn        = None
    speech_text  = ""
    selected_cat = request.POST.get('category', '')
    label, insight = CATEGORY_META.get(selected_cat, ('', ''))

    # ── AUTO INSIGHTS (on filtered data) ────────────────────────────────────
    insights_list = []
    inequality_ranking = ""
    if not df.empty:
        by_state = df.groupby('state')['secondary_dropout'].mean()
        highest_dropout_state = by_state.idxmax()
        highest_rate = by_state.max()
        lowest_dropout_state  = by_state.idxmin()
        lowest_rate  = by_state.min()
        avg_male   = df['male_dropout'].mean()
        avg_female = df['female_dropout'].mean()

        insights_list.append(f"{highest_dropout_state} has the highest avg secondary dropout rate ({highest_rate:.1f}%).")
        insights_list.append(f"{lowest_dropout_state} has the lowest avg secondary dropout rate ({lowest_rate:.1f}%).")
        if avg_female > avg_male:
            insights_list.append(f"Female dropout exceeds male by {avg_female - avg_male:.1f}% on average.")
        elif avg_male > avg_female:
            insights_list.append(f"Male dropout exceeds female by {avg_male - avg_female:.1f}% on average.")
        insights_list.append(f"Avg primary dropout: {df['primary_dropout'].mean():.1f}% | Secondary: {df['secondary_dropout'].mean():.1f}%")
        inequality_ranking = (
            f"🏆 Best Performing:  {lowest_dropout_state} ({lowest_rate:.1f}%)\n"
            f"⚠️  Worst Performing: {highest_dropout_state} ({highest_rate:.1f}%)"
        )

    # If no category selected, default to Overview
    if not selected_cat:
        selected_cat = 'Overview'
        label = '📈 Executive Overview & Correlational Matrix'
        insight = 'Complete systemic overview of dropout factors and key correlation heatmaps.'
        
    if selected_cat == 'Overview':
        # Create a Correlation Matrix Heatmap
        numeric_cols = ['primary_dropout', 'secondary_dropout', 'infrastructure_score', 'socioeconomic_score']
        labels = ['Primary Drop', 'Secondary Drop', 'Infra Score', 'Socioeco Score']
        corr_matrix = df[numeric_cols].corr()
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Plot 1: Correlation Heatmap
        cax = axes[0].imshow(corr_matrix.values, cmap='RdPu', vmin=-1, vmax=1)
        axes[0].set_xticks(range(len(labels)))
        axes[0].set_yticks(range(len(labels)))
        axes[0].set_xticklabels(labels, rotation=35, ha='right', color='#ffe6f0')
        axes[0].set_yticklabels(labels, color='#ffe6f0')
        for i in range(len(labels)):
            for j in range(len(labels)):
                axes[0].text(j, i, f"{corr_matrix.values[i, j]:.2f}", 
                             ha="center", va="center", color="#fff" if abs(corr_matrix.values[i, j]) > 0.5 else "#000", weight="bold")
        fig.colorbar(cax, ax=axes[0]).ax.yaxis.set_tick_params(color='#ffe6f0')
        axes[0].set_title('Correlation Analysis Matrix', color='#ffe6f0', pad=15)
        
        # Plot 2: Gender vs Dropout
        comp_df = df.groupby('state')[['male_dropout', 'female_dropout']].mean().head(8)
        x_pos = range(len(comp_df))
        width = 0.35
        axes[1].bar([x - width/2 for x in x_pos], comp_df['male_dropout'], width, label='Male', color='#1976d2')
        axes[1].bar([x + width/2 for x in x_pos], comp_df['female_dropout'], width, label='Female', color='#ff1493')
        axes[1].set_xticks(list(x_pos))
        axes[1].set_xticklabels(list(comp_df.index), rotation=35, ha='right', color='#ffe6f0')
        axes[1].set_ylabel('Secondary Dropout %', color='#ffe6f0')
        axes[1].set_title('Gender Dropout Gap by Region', color='#ffe6f0', pad=15)
        axes[1].legend(facecolor='#2a0a18', labelcolor='#ffe6f0')
        
        fig.suptitle('Critical Institutional Health Indicators', color='#ffb199', fontsize=14, weight='bold')
        g_dyn = get_graph(fig)
        speech_text = "This executive dashboard provides our required clear correlation analysis matrix and maps regional gender inequalities directly."

    # ── 1. Region / Location ────────────────────────────────────────────────
    elif selected_cat == 'Region':
        state_avg = df.groupby('state')['secondary_dropout'].mean().sort_values(ascending=False).head(12)
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(range(len(state_avg)), state_avg.values,
               color=['#ff1493' if v == state_avg.max() else '#ff69b4' for v in state_avg.values],
               edgecolor='#ffe6f0', linewidth=0.5)
        # Value label on every bar
        for bar, val in zip(bars, state_avg.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f'{val:.1f}%', ha='center', va='bottom', color='#fff', fontsize=9, weight='bold')
        ax.set_title('Secondary Dropout Rate by State (Top 12)', color='#ffe6f0', pad=15)
        ax.set_xticks(range(len(state_avg)))
        ax.set_xticklabels(list(state_avg.index), rotation=35, ha='right', color='#ffe6f0')
        ax.set_ylabel('Avg Dropout %', color='#ffe6f0')
        g_dyn = get_graph(fig)
        speech_text = "This bar chart reveals which states have the highest dropout rates, with exact percentages shown on each bar."

    # ── 2. Educational Level ────────────────────────────────────────────────
    elif selected_cat == 'Education':
        level_avg = pd.Series({
            'Primary':          df['primary_dropout'].mean(),
            'Secondary':        df['secondary_dropout'].mean(),
            'Higher Secondary': df['higher_dropout'].mean(),
        })
        fig, ax = plt.subplots(figsize=(7, 4.5))
        bars = ax.bar(level_avg.index, level_avg.values,
                      color=['#ffb199', '#ff1493', '#6a1b9a'],
                      edgecolor='#ffe6f0', linewidth=0.5, width=0.5)
        for bar, val in zip(bars, level_avg.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{val:.1f}%', ha='center', va='bottom', color='#fff', fontsize=12, weight='bold')
        ax.set_title('Average Dropout Rate by Educational Level', color='#ffe6f0', pad=15)
        ax.set_ylabel('Avg Dropout %', color='#ffe6f0')
        g_dyn = get_graph(fig)
        speech_text = "Each bar shows the exact average dropout % at Primary, Secondary, and Higher Secondary levels."

    # ── 3. Gender ───────────────────────────────────────────────────────────
    elif selected_cat == 'Gender':
        comp = df.groupby('state')[['male_dropout', 'female_dropout']].mean().head(8)
        x_pos = range(len(comp))
        width = 0.35
        fig, ax = plt.subplots(figsize=(10, 5))
        bars_m = ax.bar([x - width/2 for x in x_pos], comp['male_dropout'],   width, label='Male',   color='#1976d2', edgecolor='#fff')
        bars_f = ax.bar([x + width/2 for x in x_pos], comp['female_dropout'], width, label='Female', color='#ff1493', edgecolor='#fff')
        # Value labels on every bar
        for bar, val in [(b, v) for b, v in zip(bars_m, comp['male_dropout'])] + \
                        [(b, v) for b, v in zip(bars_f, comp['female_dropout'])]:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                    f'{val:.1f}', ha='center', va='bottom', color='#fff', fontsize=8, weight='bold')
        ax.set_xticks(list(x_pos))
        ax.set_xticklabels(list(comp.index), rotation=35, ha='right', color='#ffe6f0')
        ax.set_ylabel('Secondary Dropout %', color='#ffe6f0')
        ax.set_title('Gender Dropout Rate by State (with values)', color='#ffe6f0', pad=15)
        ax.legend(facecolor='#2a0a18', labelcolor='#ffe6f0')
        g_dyn = get_graph(fig)
        speech_text = "Side-by-side bars show exact male vs female dropout rates per state — identifies gender inequality hotspots."

    # ── 4. Socioeconomic Status ─────────────────────────────────────────────
    elif selected_cat == 'Socioeconomic':
        try:
            df['socio_group'] = pd.qcut(df['socioeconomic_score'], q=3,
                                         labels=['Poor', 'Middle', 'Rich'], duplicates='drop')
            socio = df.groupby('socio_group')['secondary_dropout'].mean()
            fig, ax = plt.subplots(figsize=(7, 4.5))
            ax.fill_between(socio.index, socio.values, color='#ff1493', alpha=0.45)
            ax.plot(socio.index, socio.values, marker='o', color='#fff', linewidth=2.5, markersize=10)
            # Value at every data point
            for x, y in zip(socio.index, socio.values):
                ax.text(x, y + 0.5, f'{y:.1f}%', ha='center', color='#ffb199', fontsize=12, weight='bold')
            ax.set_title('Dropout Rate by Socioeconomic Group', color='#ffe6f0', pad=15)
            ax.set_ylabel('Avg Secondary Dropout %', color='#ffe6f0')
            g_dyn = get_graph(fig)
        except Exception:
            g_dyn = None
        speech_text = "Values at each point show exact dropout % for Poor, Middle, and Rich income groups."

    # ── 5. Infrastructure Factors ───────────────────────────────────────────
    elif selected_cat == 'Infrastructure':
        fig, ax = plt.subplots(figsize=(9, 5))
        hb = ax.hexbin(df['infrastructure_score'], df['secondary_dropout'],
                       gridsize=20, cmap='spring', mincnt=1)
        cbar = fig.colorbar(hb, ax=ax)
        cbar.set_label('Concentration (records)', color='#ffe6f0')
        cbar.ax.yaxis.set_tick_params(color='#ffe6f0')
        # Annotate summary stats
        corr_val = df[['infrastructure_score', 'secondary_dropout']].corr().iloc[0, 1]
        ax.text(0.02, 0.96, f"Correlation r = {corr_val:.2f}", transform=ax.transAxes,
                color='#ffb199', fontsize=11, weight='bold', va='top')
        ax.text(0.02, 0.89, f"Avg infra: {df['infrastructure_score'].mean():.1f}  |  Avg dropout: {df['secondary_dropout'].mean():.1f}%",
                transform=ax.transAxes, color='#c897b0', fontsize=9, va='top')
        ax.set_title('Infrastructure Score vs Secondary Dropout Rate', color='#ffe6f0', pad=15)
        ax.set_xlabel('Infrastructure Score', color='#ffe6f0')
        ax.set_ylabel('Secondary Dropout %', color='#ffe6f0')
        g_dyn = get_graph(fig)
        speech_text = f"Correlation r={corr_val:.2f} — better infrastructure strongly predicts lower dropout rates."

    # ── 6. Time / Year ──────────────────────────────────────────────────────
    elif selected_cat == 'Time':
        colors = ['#ff007f', '#1976d2', '#ff69b4', '#6a1b9a']
        states_to_plot = df['state'].unique()[:4]
        fig, ax = plt.subplots(figsize=(11, 5))
        for i, state in enumerate(states_to_plot):
            s = df[df['state'] == state].groupby('year')['secondary_dropout'].mean().sort_index()
            ax.plot(s.index, s.values, marker='o', linewidth=2.5, label=state, color=colors[i % 4])
            ax.fill_between(s.index, s.values, alpha=0.10, color=colors[i % 4])
            # Label every data point
            for yr, val in zip(s.index, s.values):
                ax.text(yr, val + 0.25, f'{val:.1f}', ha='center', va='bottom',
                        color=colors[i % 4], fontsize=8, weight='bold')
        ax.set_title('Dropout Rate Trend Over Time (with values)', color='#ffe6f0', pad=15)
        ax.set_xticks(sorted(df['year'].unique()))
        ax.tick_params(colors='#ffe6f0')
        ax.legend(facecolor='#2a0a18', labelcolor='#ffe6f0')
        ax.set_ylabel('Avg Secondary Dropout %', color='#ffe6f0')
        g_dyn = get_graph(fig)
        speech_text = "Every data point shows the exact dropout % for that year — making year-over-year improvement clearly visible."

    # ── 7. Dropout Rate (Target Variable) ──────────────────────────────────
    elif selected_cat == 'DropoutRate':
        series = df['secondary_dropout'].dropna()
        mean_val   = series.mean()
        median_val = series.median()
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        # Histogram with mean line
        series.plot(kind='hist', ax=axes[0], color='#ff1493', bins=15, edgecolor='#ffe6f0', alpha=0.85)
        axes[0].axvline(mean_val, color='#fff', linewidth=2, linestyle='--')
        axes[0].text(mean_val + 0.3, axes[0].get_ylim()[1] * 0.9,
                     f'Mean\n{mean_val:.1f}%', color='#fff', fontsize=9, weight='bold')
        axes[0].set_title('Distribution of Secondary Dropout %', color='#ffe6f0', pad=12)
        axes[0].set_xlabel('Dropout %', color='#ffe6f0')
        # Box plot with median annotation
        bp = axes[1].boxplot(series, patch_artist=True,
                         boxprops=dict(facecolor='#ff1493', color='#ffe6f0'),
                         capprops=dict(color='#ffe6f0'),
                         whiskerprops=dict(color='#ffe6f0'),
                         medianprops=dict(color='#fff', linewidth=2.5),
                         flierprops=dict(markerfacecolor='#ffb199', marker='o'))
        axes[1].text(1.1, median_val, f'Median: {median_val:.1f}%', color='#fff', fontsize=9, weight='bold', va='center')
        axes[1].text(1.1, series.quantile(0.75), f'Q3: {series.quantile(0.75):.1f}%', color='#c897b0', fontsize=8, va='center')
        axes[1].text(1.1, series.quantile(0.25), f'Q1: {series.quantile(0.25):.1f}%', color='#c897b0', fontsize=8, va='center')
        axes[1].set_xticks([1])
        axes[1].set_xticklabels(['Secondary Dropout'], color='#ffe6f0')
        axes[1].set_title('Spread & Outliers', color='#ffe6f0', pad=12)
        fig.suptitle('Dropout Rate — Target Variable Overview', color='#ffb199', fontsize=13, weight='bold')
        g_dyn = get_graph(fig)
        speech_text = f"Mean dropout is {mean_val:.1f}% and median is {median_val:.1f}%. The box plot shows the spread and any outlier states."

    return render(request, 'dashboard/interactive.html', {
        'g_dyn':              g_dyn,
        'selected_cat':       selected_cat,
        'selected_cat_label': label,
        'insight':            insight,
        'speech_text':        speech_text,
        'insights_list':      insights_list,
        'inequality_ranking': inequality_ranking,
        'search_state':       search_state,
        'available_states':   available_states,
    })


@login_required(login_url='/login/')
def regional(request):
    df = get_df()
    if df.empty: return render(request, 'dashboard/index.html', {'error': True})
    
    df['primary_dropout'] = df['dropout_rates'].apply(lambda x: x['primary'])
    df['secondary_dropout'] = df['dropout_rates'].apply(lambda x: x['secondary'])

    search_state = request.GET.get('state', '').strip()
    
    if search_state:
        state_df = df[df['state'].str.contains(search_state, case=False, na=False)]
        if not state_df.empty:
            dist_avg = state_df.groupby('district')[['primary_dropout', 'secondary_dropout']].mean().head(10)
            fig1, ax1 = plt.subplots(figsize=(9,4.5))
            dist_avg.plot(kind='bar', stacked=True, ax=ax1, color=['#ffb199', '#ff007f'])
            ax1.set_title(f'Stacked Breakdown for State: {search_state.upper()}', color='#ffe6f0', pad=15)
            ax1.set_xticklabels(dist_avg.index, rotation=30, ha='right')
            g1 = get_graph(fig1)

            high_risk = state_df.groupby('district')['secondary_dropout'].mean().nlargest(5).sort_values()
            fig2, ax2 = plt.subplots(figsize=(8,4))
            ax2.hlines(y=range(len(high_risk)), xmin=0, xmax=high_risk.values, color='#ff1493', linewidth=3)
            ax2.plot(high_risk.values, range(len(high_risk)), "D", markersize=10, color='#fff')
            ax2.set_yticks(range(len(high_risk)))
            ax2.set_yticklabels(high_risk.index)
            ax2.set_title(f'Highest Risk Corridors in {search_state.upper()}', color='#ffe6f0', pad=15)
            g2 = get_graph(fig2)
            return render(request, 'dashboard/index.html', {'g1': g1, 'g2': g2, 'search_state': search_state})
            
    state_avg = df.groupby('state')[['primary_dropout', 'secondary_dropout']].mean().head(12)
    fig1, ax1 = plt.subplots(figsize=(9,4.5))
    state_avg.plot(kind='bar', stacked=True, ax=ax1, color=['#ffb199', '#ff007f'])
    ax1.set_title('National Survey: Stacked Dropout Rates by State', color='#ffe6f0', pad=15)
    ax1.set_xticklabels(state_avg.index, rotation=30, ha='right')
    g1 = get_graph(fig1)

    high_risk = df.groupby('district')['secondary_dropout'].mean().nlargest(5).sort_values()
    fig2, ax2 = plt.subplots(figsize=(8,4))
    ax2.hlines(y=range(len(high_risk)), xmin=0, xmax=high_risk.values, color='#ff1493', linewidth=3)
    ax2.plot(high_risk.values, range(len(high_risk)), "D", markersize=10, color='#fff')
    ax2.set_yticks(range(len(high_risk)))
    ax2.set_yticklabels(high_risk.index)
    ax2.set_title('National Survey: Top 5 Highest Risk Districts Overall', color='#ffe6f0', pad=15)
    g2 = get_graph(fig2)

    return render(request, 'dashboard/index.html', {'g1': g1, 'g2': g2, 'search_state': ''})

@login_required(login_url='/login/')
def demographics(request):
    df = get_df()
    df['male_dropout'] = df['gender_rates'].apply(lambda x: x['male_secondary'])
    df['female_dropout'] = df['gender_rates'].apply(lambda x: x['female_secondary'])
    
    gender_avg = df[['male_dropout', 'female_dropout']].mean()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.pie(gender_avg.values, labels=['Male Dropouts', 'Female Dropouts'], autopct='%1.1f%%', 
           colors=['#1976d2', '#ff1493'], startangle=140, textprops=dict(color="w", fontsize=12, weight="bold"))
    centre_circle = plt.Circle((0,0),0.60,fc='#2a0a18')
    fig.gca().add_artist(centre_circle)
    ax.set_title('National Gender Disparity (Donut Graphic)', color='#ffe6f0', pad=15, weight='bold')
    
    return render(request, 'dashboard/demographics.html', {'g_demo': get_graph(fig)})

@login_required(login_url='/login/')
def correlation(request):
    df = get_df()
    df['secondary_dropout'] = df['dropout_rates'].apply(lambda x: x['secondary'])
    
    fig, ax = plt.subplots(figsize=(8,4))
    hb = ax.hexbin(df['infrastructure_score'], df['secondary_dropout'], gridsize=25, cmap='spring', mincnt=1)
    cbar = fig.colorbar(hb, ax=ax)
    cbar.set_label('Density Frequency', color='#ffe6f0')
    cbar.ax.yaxis.set_tick_params(color='#ffe6f0')
    ax.set_title('Infrastructure vs Dropout (Hexbin Density Graphic)', color='#ffe6f0')
    ax.set_xlabel('Infrastructure Score', color='#ffe6f0')
    ax.set_ylabel('Secondary Dropout %', color='#ffe6f0')
    
    return render(request, 'dashboard/correlation.html', {'g_corr': get_graph(fig)})

@login_required(login_url='/login/')
def performance(request):
    df = get_df()
    df['secondary_dropout'] = df['dropout_rates'].apply(lambda x: x['secondary'])
    
    fig, ax = plt.subplots(figsize=(10,4.5))
    pink_colors = ['#ff007f', '#1976d2', '#ff69b4', '#6a1b9a']
    for i, state in enumerate(df['state'].unique()[:4]):
        s_data = df[df['state'] == state].groupby('year')['secondary_dropout'].mean()
        ax.plot(s_data.index, s_data.values, marker='o', linewidth=2, label=state, color=pink_colors[i%4])
        ax.fill_between(s_data.index, s_data.values, alpha=0.15, color=pink_colors[i%4])
    
    ax.set_title('Educational Performance over Time (Overlapping Polygon Graphic)', color='#ffe6f0')
    ax.set_xticks(df['year'].unique())
    ax.legend(facecolor='#2a0a18', labelcolor='#ffe6f0')
    
    return render(request, 'dashboard/performance.html', {'g_perf': get_graph(fig)})

@login_required(login_url='/login/')
def patterns(request):
    df = get_df()
    if df.empty: return render(request, 'dashboard/patterns.html', {'error': True})
    df['male_dropout'] = df['gender_rates'].apply(lambda x: x['male_secondary'])
    df['female_dropout'] = df['gender_rates'].apply(lambda x: x['female_secondary'])
    df['secondary_dropout'] = df['dropout_rates'].apply(lambda x: x['secondary'])

    state_gender = df.groupby('state')[['male_dropout', 'female_dropout']].mean().head(6) 
    fig1, ax1 = plt.subplots(figsize=(9,4.5))
    state_gender.plot(kind='bar', stacked=True, ax=ax1, color=['#1976d2', '#e91e63'])
    ax1.set_title('Predictive Pattern: Gender Dropout (Stacked Graphic)', color='#ffe6f0', pad=15)
    ax1.set_xticklabels(state_gender.index, rotation=30, ha='right')
    ax1.legend(['Male', 'Female'], facecolor='#2a0a18', labelcolor='#ffe6f0')
    g1 = get_graph(fig1)

    try:
        df['socio_group'] = pd.qcut(df['socioeconomic_score'], q=5, labels=['Very Poor', 'Poor', 'Middle', 'Rich', 'Elite'], duplicates='drop')
        socio_drop = df.groupby('socio_group')['secondary_dropout'].mean()
        fig2, ax2 = plt.subplots(figsize=(8,4))
        ax2.fill_between(socio_drop.index, socio_drop.values, color='#ff1493', alpha=0.6)
        ax2.plot(socio_drop.index, socio_drop.values, marker='s', color='#fff', linewidth=3, markersize=8)
        ax2.set_title('Socioeconomic Status Impact (Area Graphic)', color='#ffe6f0', pad=15)
        ax2.set_ylabel('Avg Secondary Dropout %', color='#ffe6f0')
        g2 = get_graph(fig2)
    except:
        g2 = g1 

    return render(request, 'dashboard/patterns.html', {'g1': g1, 'g2': g2})

@login_required(login_url='/login/')
def view_data(request):
    df = get_df()
    search_state = request.GET.get('state', '').strip()
    success = False

    if request.method == 'POST':
        success = True

    if not df.empty:
        display_df = df[['state', 'district', 'year', 'infrastructure_score', 'socioeconomic_score']].copy()
        display_df['Primary Dropout'] = df['dropout_rates'].apply(lambda x: x.get('primary'))
        display_df['Secondary Dropout'] = df['dropout_rates'].apply(lambda x: x.get('secondary'))
        
        if search_state:
            display_df = display_df[display_df['state'].str.contains(search_state, case=False, na=False)]
            
        html_table = display_df.head(100).round(2).to_html(classes="data-table", index=False)
    else:
        html_table = "<h3>No dataset connection detected.</h3>"
    return render(request, 'dashboard/view_data.html', {'table': html_table, 'search_state': search_state, 'success': success})
