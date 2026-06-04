using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.Web.WebView2.Core;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace GyroDynamoWinUI;

/// <summary>
/// The main content page displayed inside the application window.
/// Add your UI logic, event handlers, and data binding here.
/// </summary>
public sealed partial class MainPage : Page
{
    private const string VirtualHostName = "gyro-dynamo.local";
    private bool _controlsReady;
    private bool _pageReady;

    public MainPage()
    {
        InitializeComponent();
    }

    private async void Page_Loaded(object sender, RoutedEventArgs e)
    {
        InitializeControls();
        await InitializeVisualizerAsync();
    }

    private void InitializeControls()
    {
        _controlsReady = false;

        ThemeComboBox.SelectedIndex = 0;
        TrailComboBox.SelectedIndex = 1;
        OrientationComboBox.SelectedIndex = 2;

        SensitivitySlider.Value = 1.0;
        SmoothingSlider.Value = 0.15;
        DeadZoneSlider.Value = 0.5;
        BpmSlider.Value = 84;
        TempoScaleSlider.Value = 1;
        BeatsPerMeasureSlider.Value = 8;
        AlignBarsSlider.Value = 4;
        RingCountSlider.Value = 7;
        GyroScaleSlider.Value = 1;
        WobbleSlider.Value = 0.35;
        ShakeSlider.Value = 0;
        HudToggle.IsOn = true;
        DebugToggle.IsOn = false;

        UpdateSliderLabels();
        _controlsReady = true;
    }

    private async Task InitializeVisualizerAsync()
    {
        try
        {
            string webContentPath = Path.Combine(AppContext.BaseDirectory, "WebContent");
            string indexPath = Path.Combine(webContentPath, "index.html");

            if (!File.Exists(indexPath))
            {
                ShowError($"Missing packaged web content: {indexPath}");
                return;
            }

            await VisualizerWebView.EnsureCoreWebView2Async();
            VisualizerWebView.CoreWebView2.SetVirtualHostNameToFolderMapping(
                VirtualHostName,
                webContentPath,
                CoreWebView2HostResourceAccessKind.Allow);
            VisualizerWebView.CoreWebView2.Navigate($"https://{VirtualHostName}/index.html");
            StatusText.Text = $"Loading {indexPath}";
        }
        catch (Exception ex)
        {
            ShowError(ex.Message);
        }
    }

    private async void VisualizerWebView_NavigationCompleted(WebView2 sender, CoreWebView2NavigationCompletedEventArgs args)
    {
        LoadingRing.IsActive = false;
        LoadingRing.Visibility = Visibility.Collapsed;

        if (!args.IsSuccess)
        {
            ShowError($"Navigation failed: {args.WebErrorStatus}");
            return;
        }

        _pageReady = true;
        ErrorInfoBar.IsOpen = false;
        StatusText.Text = "Visualizer ready. Use the WinUI controls or interact directly with the canvas.";
        await SyncAllSettingsAsync();
    }

    private async Task SyncAllSettingsAsync()
    {
        await SetSettingAsync("theme", SelectedTag(ThemeComboBox));
        await SetSettingAsync("trailLength", SelectedTag(TrailComboBox));
        await SetSettingAsync("orientationMode", SelectedTag(OrientationComboBox));
        await SetSettingAsync("sensitivity", SensitivitySlider.Value);
        await SetSettingAsync("smoothing", SmoothingSlider.Value);
        await SetSettingAsync("deadZoneDegrees", DeadZoneSlider.Value);
        await SetSettingAsync("bpm", (int)Math.Round(BpmSlider.Value));
        await SetSettingAsync("tempoScale", TempoScaleSlider.Value);
        await SetSettingAsync("beatsPerMeasure", (int)Math.Round(BeatsPerMeasureSlider.Value));
        await SetSettingAsync("alignBars", (int)Math.Round(AlignBarsSlider.Value));
        await SetSettingAsync("ringCount", (int)Math.Round(RingCountSlider.Value));
        await SetSettingAsync("gyroScale", GyroScaleSlider.Value);
        await SetSettingAsync("wobble", WobbleSlider.Value);
        await SetSettingAsync("visualShake", ShakeSlider.Value);
        await SetSettingAsync("showHUD", HudToggle.IsOn);
        await SetSettingAsync("debugHUD", DebugToggle.IsOn);
    }

    private async Task<bool> RunBridgeCommandAsync(string command)
    {
        return await ExecuteBridgeAsync($"bridge.{command}()");
    }

    private async Task<bool> SetSettingAsync<T>(string key, T value)
    {
        string keyJson = JsonSerializer.Serialize(key);
        string valueJson = JsonSerializer.Serialize(value);
        return await ExecuteBridgeAsync($"bridge.setSetting({keyJson}, {valueJson})");
    }

    private async Task<bool> ExecuteBridgeAsync(string bridgeExpression)
    {
        if (!_pageReady)
        {
            StatusText.Text = "Visualizer is still loading.";
            return false;
        }

        try
        {
            string script =
                "(() => {" +
                "const bridge = window.gyroDynamoWinUiBridge;" +
                "if (!bridge) throw new Error(\"GyroDynamo WinUI bridge is not available.\");" +
                $"return {bridgeExpression};" +
                "})()";
            await VisualizerWebView.ExecuteScriptAsync(script);
            ErrorInfoBar.IsOpen = false;
            return true;
        }
        catch (Exception ex)
        {
            ShowError(ex.Message);
            return false;
        }
    }

    private static string SelectedTag(ComboBox comboBox)
    {
        return (comboBox.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? string.Empty;
    }

    private void ShowError(string message)
    {
        ErrorInfoBar.Message = message;
        ErrorInfoBar.IsOpen = true;
        StatusText.Text = message;
    }

    private void UpdateSliderLabels()
    {
        SensitivityValue.Text = $"Sensitivity {SensitivitySlider.Value:F1}";
        SmoothingValue.Text = $"Smoothing {SmoothingSlider.Value:F2}";
        DeadZoneValue.Text = $"Dead Zone {DeadZoneSlider.Value:F1} deg";
        BpmValue.Text = $"BPM {(int)Math.Round(BpmSlider.Value)}";
        TempoScaleValue.Text = $"Tempo {TempoScaleSlider.Value:F2}x";
        BeatsPerMeasureValue.Text = $"Beats / Measure {(int)Math.Round(BeatsPerMeasureSlider.Value)}";
        AlignBarsValue.Text = $"Align Every {(int)Math.Round(AlignBarsSlider.Value)} Bars";
        RingCountValue.Text = $"Rings {(int)Math.Round(RingCountSlider.Value)}";
        GyroScaleValue.Text = $"Scale {GyroScaleSlider.Value:F2}";
        WobbleValue.Text = $"Wobble {WobbleSlider.Value:F2}";
        ShakeValue.Text = $"Shake {ShakeSlider.Value:F2}";
    }

    private async void StartInput_Click(object sender, RoutedEventArgs e)
    {
        if (await RunBridgeCommandAsync("startInput")) StatusText.Text = "Desktop input active.";
    }

    private async void Demo_Click(object sender, RoutedEventArgs e)
    {
        if (await RunBridgeCommandAsync("demoMode")) StatusText.Text = "Demo mode active.";
    }

    private async void Calibrate_Click(object sender, RoutedEventArgs e)
    {
        if (await RunBridgeCommandAsync("calibrate")) StatusText.Text = "Calibration requested.";
    }

    private async void StopInput_Click(object sender, RoutedEventArgs e)
    {
        if (await RunBridgeCommandAsync("stopInput")) StatusText.Text = "Input stopped.";
    }

    private async void ResetRig_Click(object sender, RoutedEventArgs e)
    {
        if (!_controlsReady) return;

        _controlsReady = false;
        BpmSlider.Value = 84;
        TempoScaleSlider.Value = 1;
        BeatsPerMeasureSlider.Value = 8;
        AlignBarsSlider.Value = 4;
        RingCountSlider.Value = 7;
        GyroScaleSlider.Value = 1;
        WobbleSlider.Value = 0.35;
        ShakeSlider.Value = 0;
        UpdateSliderLabels();
        _controlsReady = true;

        if (await RunBridgeCommandAsync("resetRig")) StatusText.Text = "Rig reset.";
    }

    private async void ThemeComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_controlsReady) return;
        await SetSettingAsync("theme", SelectedTag(ThemeComboBox));
    }

    private async void TrailComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_controlsReady) return;
        await SetSettingAsync("trailLength", SelectedTag(TrailComboBox));
    }

    private async void OrientationComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_controlsReady) return;
        await SetSettingAsync("orientationMode", SelectedTag(OrientationComboBox));
    }

    private async void SensitivitySlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("sensitivity", SensitivitySlider.Value);
    }

    private async void SmoothingSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("smoothing", SmoothingSlider.Value);
    }

    private async void DeadZoneSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("deadZoneDegrees", DeadZoneSlider.Value);
    }

    private async void BpmSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("bpm", (int)Math.Round(BpmSlider.Value));
    }

    private async void TempoScaleSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("tempoScale", TempoScaleSlider.Value);
    }

    private async void BeatsPerMeasureSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("beatsPerMeasure", (int)Math.Round(BeatsPerMeasureSlider.Value));
    }

    private async void AlignBarsSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("alignBars", (int)Math.Round(AlignBarsSlider.Value));
    }

    private async void RingCountSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("ringCount", (int)Math.Round(RingCountSlider.Value));
    }

    private async void GyroScaleSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("gyroScale", GyroScaleSlider.Value);
    }

    private async void WobbleSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("wobble", WobbleSlider.Value);
    }

    private async void ShakeSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (!_controlsReady) return;
        UpdateSliderLabels();
        await SetSettingAsync("visualShake", ShakeSlider.Value);
    }

    private async void HudToggle_Toggled(object sender, RoutedEventArgs e)
    {
        if (!_controlsReady) return;
        await SetSettingAsync("showHUD", HudToggle.IsOn);
    }

    private async void DebugToggle_Toggled(object sender, RoutedEventArgs e)
    {
        if (!_controlsReady) return;
        await SetSettingAsync("debugHUD", DebugToggle.IsOn);
    }
}
